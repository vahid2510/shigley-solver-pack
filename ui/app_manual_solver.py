import json
import inspect
import sys
import uuid
import functools
import io
import zipfile
from pathlib import Path
from typing import Any

import html as html_lib
import streamlit as st
from streamlit.components.v1 import html as st_html
from solvers.registry import REGISTRY


# ---------------------------------------------------------------------------
# Optional parser imports (for automatic detection from text problems)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSER_ROOT = PROJECT_ROOT / "problem_parsing_env"
build_spec = None
solve_spec = None

if PARSER_ROOT.exists():
    sys.path.insert(0, str(PARSER_ROOT))
    try:
        from builder_core import build_spec  # type: ignore
        from solver_core import solve as solve_spec  # type: ignore
    except Exception:  # pragma: no cover - fallback for partial installs
        build_spec = None
        solve_spec = None


st.set_page_config(page_title="Shigley Solver Pack", page_icon="[]", layout="wide")
st.title("Shigley Solver Pack - Manual & Auto Solvers")

st.sidebar.markdown("**Reference book:** Shigley's Mechanical Engineering Design")
st.sidebar.markdown("**Creator:** vahid ahmadi khorami")

HELP_ROOT = PROJECT_ROOT / "docs" / "help"
HELP_INDEX = HELP_ROOT / "index.html"

MANUAL_RAW_HTML = ""
MANUAL_EMBED_HTML = ""
MANUAL_ZIP_BYTES: bytes = b""
MANUAL_LOAD_ERROR = ""
MANUAL_AVAILABLE = False
MANUAL_URI = ""

DEFAULT_THEME = "Midnight Dark"

THEME_CSS = {
    DEFAULT_THEME: """
    <style id="shigley-theme-css">
    :root {
        color-scheme: dark;
    }

    body, .stApp, [data-testid="stAppViewContainer"] {
        background: #0b1120;
        color: #e2e8f0;
    }

    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }

    [data-testid="stSidebar"] {
        background: #111827;
        color: #e2e8f0;
        box-shadow: 4px 0 18px rgba(2, 6, 23, 0.55);
    }

    [data-testid="stHeader"] {
        background: rgba(15, 23, 42, 0.92);
        border-bottom: 1px solid rgba(148, 163, 184, 0.25);
    }

    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc;
    }

    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li, .stMarkdown pre {
        color: #e2e8f0;
    }

    .stAlert p,
    .stInfo {
        color: #e2e8f0;
    }

    label, .stTextInput label, .stSelectbox label, .stTextArea label {
        color: #f1f5f9;
        font-weight: 600;
    }

    code {
        color: #f8fafc;
    }

    pre, code {
        background: #1e293b;
        border-radius: 8px;
    }

    textarea, input, select, .stTextArea textarea {
        background: #16213d !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        box-shadow: inset 0 1px 2px rgba(2, 6, 23, 0.45);
    }

    textarea::placeholder, input::placeholder {
        color: #94a3b8;
    }

    .stTabs [data-baseweb="tab"] {
        color: #cbd5f5;
        font-weight: 600;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #60a5fa;
    }

    .stTabs [aria-selected="true"] {
        color: #60a5fa !important;
        border-bottom: 3px solid #60a5fa !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    .print-report-button {
        background: linear-gradient(135deg, #2563eb, #8b5cf6);
        color: #f8fafc;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.45rem 1.4rem;
        box-shadow: 0 10px 24px rgba(37, 99, 235, 0.35);
        transition: transform 0.1s ease-in-out, box-shadow 0.1s ease-in-out;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .print-report-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 34px rgba(37, 99, 235, 0.48);
    }
    </style>
    
    """,
}

AVAILABLE_CLASSES = sorted(REGISTRY.keys())


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def quant(value: float, unit: str, si: float) -> dict:
    """Create a tiny quantity dict compatible with solver helpers."""
    return {"value": value, "unit": unit, "si": si}


def default_inputs_by_class() -> dict[str, dict]:
    """Provide lightweight ready-to-run examples for every solver."""
    return {
        "beam.eb.simply_supported.udl": {
            "geometry": {
                "L": quant(2.0, "m", 2.0),
                "section": {
                    "b": quant(40.0, "mm", 0.04),
                    "h": quant(60.0, "mm", 0.06),
                },
            },
            "material": {"E": quant(210.0, "GPa", 210e9)},
            "loads": [{"type": "uniform", "q": quant(5.0, "kN/m", 5000.0)}],
        },
        "beam.eb.simply_supported.point_mid": {
            "geometry": {
                "L": quant(2.5, "m", 2.5),
                "section": {"b": quant(50.0, "mm", 0.05), "h": quant(75.0, "mm", 0.075)},
            },
            "material": {"E": quant(200.0, "GPa", 200e9)},
            "loads": [{"type": "point", "at": "mid", "P": quant(12.0, "kN", 12000.0)}],
        },
        "beam.cantilever.point_end": {
            "geometry": {
                "L": quant(1.5, "m", 1.5),
                "section": {"b": quant(30.0, "mm", 0.03), "h": quant(90.0, "mm", 0.09)},
            },
            "material": {"E": quant(190.0, "GPa", 190e9)},
            "loads": [{"type": "point", "at": "free", "P": quant(4.0, "kN", 4000.0)}],
        },
        "shaft.torsion.solid": {
            "geometry": {"L": quant(0.5, "m", 0.5), "d": quant(40.0, "mm", 0.04)},
            "material": {"G": quant(80.0, "GPa", 80e9)},
            "loads": {"T": quant(1200.0, "N*m", 1200.0)},
        },
        "shaft.torsion.hollow": {
            "geometry": {
                "L": quant(0.8, "m", 0.8),
                "do": quant(60.0, "mm", 0.06),
                "di": quant(30.0, "mm", 0.03),
            },
            "material": {"G": quant(82.0, "GPa", 82e9)},
            "loads": {"T": quant(900.0, "N*m", 900.0)},
        },
        "power.screw.raise": {
            "geometry": {
                "d_m": quant(36.0, "mm", 0.036),
                "lead": quant(6.0, "mm", 0.006),
                "d_collar": quant(60.0, "mm", 0.06),
                "n_starts": quant(1, "-", 1.0),
            },
            "tribology": {
                "mu": quant(0.15, "-", 0.15),
                "mu_collar": quant(0.08, "-", 0.08),
            },
            "loads": {"F": quant(25.0, "kN", 25_000.0)},
        },
        "shaft.design.d_required_static": {
            "loads": {"M": quant(2.8e3, "N*m", 2800.0), "T": quant(1.6e3, "N*m", 1600.0)},
            "material": {"S_y": quant(350.0, "MPa", 350e6)},
            "design": {"n": quant(2.0, "-", 2.0)},
            "stress_conc": {"Kt": quant(1.6, "-", 1.6), "Kts": quant(1.4, "-", 1.4)},
            "factors": {"C_b": quant(1.0, "-", 1.0), "C_t": quant(1.0, "-", 1.0)},
        },
        "shaft.design.d_required_fatigue": {
            "loads": {
                "M_a": quant(1.8e3, "N*m", 1800.0),
                "M_m": quant(1.0e3, "N*m", 1000.0),
                "T_a": quant(1.2e3, "N*m", 1200.0),
                "T_m": quant(800.0, "N*m", 800.0),
            },
            "material": {
                "S_ut": quant(620.0, "MPa", 620e6),
                "S_y": quant(420.0, "MPa", 420e6),
                "S_e": quant(210.0, "MPa", 210e6),
            },
            "design": {"n": quant(2.0, "-", 2.0)},
            "stress_conc": {"Kt": quant(1.5, "-", 1.5), "Kts": quant(1.4, "-", 1.4)},
            "notch_sensitivity": {"q_a": quant(0.85, "-", 0.85), "q_s": quant(0.9, "-", 0.9)},
        },
        "failure.von_mises": {
            "stress": {
                "sx": quant(180.0, "MPa", 180e6),
                "sy": quant(60.0, "MPa", 60e6),
                "sz": quant(0.0, "MPa", 0.0),
                "txy": quant(45.0, "MPa", 45e6),
            },
            "material": {"S_y": quant(350.0, "MPa", 350e6)},
        },
        "failure.tresca": {
            "principal": {
                "s1": quant(220.0, "MPa", 220e6),
                "s2": quant(30.0, "MPa", 30e6),
                "s3": quant(-20.0, "MPa", -20e6),
            },
            "material": {"S_y": quant(300.0, "MPa", 300e6)},
        },
        "fatigue.endurance_modified": {
            "material": {
                "S_e_prime": quant(340.0, "MPa", 340e6),
            },
            "marin": {
                "k_a": quant(0.85, "-", 0.85),
                "k_b": quant(0.9, "-", 0.9),
                "k_c": quant(1.0, "-", 1.0),
                "k_d": quant(0.95, "-", 0.95),
                "k_e": quant(1.0, "-", 1.0),
                "k_f": quant(0.9, "-", 0.9),
            },
        },
        "fatigue.goodman": {
            "loads": {"S_a": quant(110.0, "MPa", 110e6), "S_m": quant(60.0, "MPa", 60e6)},
            "material": {"S_ut": quant(550.0, "MPa", 550e6), "S_e": quant(240.0, "MPa", 240e6)},
        },
        "fatigue.gerber": {
            "loads": {"S_a": quant(120.0, "MPa", 120e6), "S_m": quant(70.0, "MPa", 70e6)},
            "material": {"S_ut": quant(600.0, "MPa", 600e6), "S_e": quant(230.0, "MPa", 230e6)},
        },
        "fatigue.soderberg": {
            "loads": {"S_a": quant(90.0, "MPa", 90e6), "S_m": quant(45.0, "MPa", 45e6)},
            "material": {"S_y": quant(360.0, "MPa", 360e6), "S_e": quant(200.0, "MPa", 200e6)},
        },
        "spring.helical.compression": {
            "geometry": {
                "d": quant(6.0, "mm", 0.006),
                "D": quant(60.0, "mm", 0.06),
                "n_a": quant(8.0, "-", 8.0),
            },
            "material": {"G": quant(79.0, "GPa", 79e9)},
            "loads": {"F": quant(500.0, "N", 500.0)},
        },
        "spring.helical.extension": {
            "geometry": {
                "d": quant(5.5, "mm", 0.0055),
                "D": quant(45.0, "mm", 0.045),
                "n_a": quant(9.0, "-", 9.0),
            },
            "material": {"G": quant(80.0, "GPa", 80e9)},
            "loads": {
                "F": quant(420.0, "N", 420.0),
                "F_initial": quant(90.0, "N", 90.0),
            },
        },
        "spring.helical.torsion": {
            "geometry": {
                "d": quant(6.0, "mm", 0.006),
                "D": quant(50.0, "mm", 0.05),
                "n_a": quant(7.0, "-", 7.0),
            },
            "material": {"G": quant(79.0, "GPa", 79e9)},
            "loads": {"M": quant(35.0, "N*m", 35.0)},
        },
        "spring.helical.parallel": {
            "springs": {
                "spring1": {
                    "geometry": {
                        "d": quant(6.0, "mm", 0.006),
                        "D": quant(55.0, "mm", 0.055),
                        "n_a": quant(8.0, "-", 8.0),
                    },
                    "material": {"G": quant(79.0, "GPa", 79e9)},
                },
                "spring2": {
                    "geometry": {
                        "d": quant(5.0, "mm", 0.005),
                        "D": quant(40.0, "mm", 0.04),
                        "n_a": quant(10.0, "-", 10.0),
                    },
                    "material": {"G": quant(80.0, "GPa", 80e9)},
                },
            },
            "loads": {"F_total": quant(900.0, "N", 900.0)},
        },
        "shaft.analysis.segmented": {
            "segments": [
                {"length": 0.12, "d_o": 0.035},
                {"length": 0.25, "d_o": 0.045},
                {"length": 0.18, "d_o": 0.04}
            ],
            "supports": [
                {"label": "A", "x": 0.05},
                {"label": "B", "x": 0.45}
            ],
            "loads": [
                {"type": "gear", "x": 0.18, "r": 0.04, "F_t": 3800.0, "F_r": 2100.0},
                {"type": "point_force", "x": 0.32, "Fz": 1500.0},
                {"type": "torque", "x": 0.45, "T": 950.0}
            ],
            "material": {
                "S_y": quant(420.0, "MPa", 420e6),
                "S_ut": quant(620.0, "MPa", 620e6),
                "G": quant(79.0, "GPa", 79e9)
            },
            "design": {
                "fatigue": {
                    "M_a": quant(120.0, "N*m", 120.0),
                    "M_m": quant(60.0, "N*m", 60.0),
                    "T_a": quant(450.0, "N*m", 450.0),
                    "T_m": quant(600.0, "N*m", 600.0),
                    "Kt": quant(1.6, "-", 1.6),
                    "Kts": quant(1.3, "-", 1.3),
                    "q_a": quant(0.85, "-", 0.85),
                    "q_s": quant(0.9, "-", 0.9),
                    "Se_prime": quant(310.0, "MPa", 310e6),
                    "marin": {
                        "k_surface": quant(0.9, "-", 0.9),
                        "k_size": quant(0.85, "-", 0.85),
                        "k_load": quant(1.0, "-", 1.0),
                        "k_temp": quant(1.0, "-", 1.0),
                        "k_reliability": quant(0.868, "-", 0.868)
                    }
                }
            }
        },
        "bearing.ball.L10": {
            "catalog": {"C": quant(20_000.0, "N", 20000.0)},
            "loads": {"P": quant(5000.0, "N", 5000.0)},
            "operating": {"rpm": quant(1800.0, "rpm", 1800.0)},
        },
        "bearing.ball.life_reliability": {
            "catalog": {"C": quant(19_000.0, "N", 19000.0)},
            "loads": {"P": quant(4500.0, "N", 4500.0)},
            "operating": {"rpm": quant(1800.0, "rpm", 1800.0)},
            "reliability": {"R": quant(0.95, "-", 0.95)},
            "bearing": {"p": quant(3.0, "-", 3.0)},
        },
        "bearing.ball.required_C": {
            "loads": {"P": quant(4200.0, "N", 4200.0)},
            "operating": {"rpm": quant(1500.0, "rpm", 1500.0)},
            "life": {"hours": quant(12_000.0, "hours", 12_000.0)},
            "reliability": {"R": quant(0.96, "-", 0.96)},
            "bearing": {"p": quant(3.0, "-", 3.0)},
        },
        "bearing.ball.equivalent_load": {
            "loads": {
                "F_r": quant(5000.0, "N", 5000.0),
                "F_a": quant(1200.0, "N", 1200.0),
            },
            "factors": {
                "V": quant(1.0, "-", 1.0),
                "X": quant(1.0, "-", 1.0),
                "Y": quant(1.5, "-", 1.5),
                "e": quant(0.3, "-", 0.3),
            },
        },
        "gear.spur.agma_bending_basic": {
            "loads": {"W_t": quant(3500.0, "N", 3500.0)},
            "factors": {
                "K_o": quant(1.1, "-", 1.1),
                "K_v": quant(1.2, "-", 1.2),
                "K_s": quant(1.0, "-", 1.0),
                "K_m": quant(1.3, "-", 1.3),
                "K_B": quant(1.0, "-", 1.0),
            },
            "geometry": {
                "J": quant(0.32, "-", 0.32),
                "b": quant(40.0, "mm", 0.04),
                "m": quant(5.0, "mm", 0.005),
            },
        },
        "gear.spur.agma_contact_basic": {
            "loads": {"W_t": quant(3500.0, "N", 3500.0)},
            "factors": {
                "K_o": quant(1.1, "-", 1.1),
                "K_v": quant(1.2, "-", 1.2),
                "K_s": quant(1.0, "-", 1.0),
                "K_m": quant(1.2, "-", 1.2),
                "C_f": quant(1.0, "-", 1.0),
            },
            "material": {"Z_e": quant(189.0, "MPa^0.5", 189.0)},
            "geometry": {
                "I": quant(0.12, "-", 0.12),
                "b": quant(40.0, "mm", 0.04),
                "d_p": quant(200.0, "mm", 0.2),
            },
        },
        "pv.cylinder.thin": {
            "geometry": {"R": quant(0.5, "m", 0.5), "t": quant(6.0, "mm", 0.006)},
            "loads": [{"type": "pressure", "p": quant(2.0, "MPa", 2e6)}],
            "material": {"sigma_y": quant(250.0, "MPa", 250e6)},
        },
        "pv.cylinder.thick": {
            "geometry": {"r_i": quant(0.45, "m", 0.45), "r_o": quant(0.6, "m", 0.6)},
            "loads": {"p_i": quant(12.0, "MPa", 12e6), "p_o": quant(0.1, "MPa", 0.1e6)},
        },
        "fit.press.interference": {
            "shaft": {"r_s": quant(0.05, "m", 0.05), "E": quant(210.0, "GPa", 210e9), "nu": quant(0.3, "-", 0.3)},
            "hub": {
                "r_i": quant(0.05, "m", 0.05),
                "r_o": quant(0.09, "m", 0.09),
                "E": quant(200.0, "GPa", 200e9),
                "nu": quant(0.3, "-", 0.3),
            },
            "fit": {"delta": quant(40.0, "um", 40e-6)},
        },
        "clutch.single_disc.uniform_pressure": {
            "loads": {"F": quant(12_000.0, "N", 12_000.0)},
            "tribology": {"mu": quant(0.35, "-", 0.35)},
            "geometry": {"r_i": quant(60.0, "mm", 0.06), "r_o": quant(120.0, "mm", 0.12)},
        },
        "clutch.single_disc.uniform_wear": {
            "loads": {"F": quant(12_000.0, "N", 12_000.0)},
            "tribology": {"mu": quant(0.35, "-", 0.35)},
            "geometry": {"r_i": quant(60.0, "mm", 0.06), "r_o": quant(120.0, "mm", 0.12)},
        },
        "belt.flat.power": {
            "loads": {"T1": quant(1800.0, "N", 1800.0), "T2": quant(600.0, "N", 600.0)},
            "operating": {"v": quant(12.0, "m/s", 12.0)},
        },
        "belt.flat.tension_ratio": {
            "tribology": {"mu": quant(0.3, "-", 0.3)},
            "geometry": {"theta": quant(2.8, "rad", 2.8)},
        },
        "bolt.preload_proof": {
            "geometry": {"A_t": quant(190.0, "mm^2", 190e-6), "n": quant(4, "-", 4)},
            "material": {"S_p": quant(700.0, "MPa", 700e6)},
            "loads": {"F_external": quant(15_000.0, "N", 15000.0)},
        },
        "weld.fillet.linear": {
            "geometry": {"t": quant(6.0, "mm", 0.006), "Lw": quant(120.0, "mm", 0.12)},
            "loads": {"F": quant(18_000.0, "N", 18000.0)},
        },
        "column.euler": {
            "geometry": {
                "L": quant(2.4, "m", 2.4),
                "I": quant(8_500_000.0, "mm^4", 8.5e-6),
                "K": quant(1.0, "-", 1.0),
            },
            "material": {"E": quant(200.0, "GPa", 200e9)},
        },
        "column.johnson": {
            "geometry": {
                "L": quant(1.8, "m", 1.8),
                "A": quant(3500.0, "mm^2", 3.5e-3),
                "I": quant(12_000_000.0, "mm^4", 1.2e-5),
                "K": quant(0.8, "-", 0.8),
            },
            "material": {"S_y": quant(350.0, "MPa", 350e6), "E": quant(210.0, "GPa", 210e9)},
        },
    }


DEFAULT_INPUTS = default_inputs_by_class()


def _format_math(text: str | None) -> str:
    r"""Convert legacy \( \)/\[\] syntax to $/$$ so Streamlit renders LaTeX."""
    if not text:
        return ""
    formatted = (
        text.replace(r"\[", "$$")
        .replace(r"\]", "$$")
        .replace(r"\(", "$")
        .replace(r"\)", "$")
        .replace(r"\tfrac", r"\frac")
    )
    return formatted


def _is_empty_payload(value: Any) -> bool:
    """Return True if the value is considered empty for report generation."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    if isinstance(value, dict):
        return not value
    return False


def _content_to_html(value: Any) -> str:
    """Render arbitrary Python data structures into HTML snippets suitable for printing."""
    if isinstance(value, str):
        escaped = html_lib.escape(value)
        return f'<div class="report-text-block">{escaped}</div>'
    if isinstance(value, (int, float, bool)):
        return f'<div class="report-text-block">{html_lib.escape(str(value))}</div>'
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            items = "".join(f"<li>{html_lib.escape(item)}</li>" for item in value if item.strip())
            return f"<ul>{items}</ul>" if items else ""
        try:
            pretty = json.dumps(value, indent=2, ensure_ascii=False)
        except TypeError:
            pretty = str(value)
        return f"<pre>{html_lib.escape(pretty)}</pre>"
    if isinstance(value, dict):
        try:
            pretty = json.dumps(value, indent=2, ensure_ascii=False)
        except TypeError:
            pretty = str(value)
        return f"<pre>{html_lib.escape(pretty)}</pre>"
    return f"<pre>{html_lib.escape(str(value))}</pre>"


def _build_manual_zip() -> bytes:
    resources = [
        "index.html",
        "style.css",
        "help.js",
        "Manual.hhp",
        "Manual.hhc",
        "Manual.hhk",
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel_path in resources:
            file_path = HELP_ROOT / rel_path
            if file_path.exists():
                archive.writestr(rel_path, file_path.read_bytes())
    buffer.seek(0)
    return buffer.getvalue()


if HELP_INDEX.exists():
    try:
        MANUAL_RAW_HTML = HELP_INDEX.read_text(encoding="utf-8")
        MANUAL_EMBED_HTML = MANUAL_RAW_HTML
        style_path = HELP_ROOT / "style.css"
        if style_path.exists():
            style_tag = f"<style>\n{style_path.read_text(encoding='utf-8')}\n</style>"
            css_patterns = [
                '<link rel="stylesheet" href="style.css" />',
                '<link rel="stylesheet" href="style.css"/>',
                "<link rel='stylesheet' href='style.css' />",
                "<link rel='stylesheet' href='style.css'/>",
            ]
            replaced = False
            for pattern in css_patterns:
                if pattern in MANUAL_EMBED_HTML:
                    MANUAL_EMBED_HTML = MANUAL_EMBED_HTML.replace(pattern, style_tag)
                    replaced = True
            if not replaced:
                MANUAL_EMBED_HTML = MANUAL_EMBED_HTML.replace("</head>", f"{style_tag}\n</head>")
        script_path = HELP_ROOT / "help.js"
        if script_path.exists():
            script_content = script_path.read_text(encoding="utf-8")
            script_tag = f"<script>\n{script_content}\n</script>"
            script_patterns = [
                '<script defer src="help.js"></script>',
                '<script src="help.js"></script>',
                "<script defer src='help.js'></script>",
                "<script src='help.js'></script>",
            ]
            for pattern in script_patterns:
                if pattern in MANUAL_EMBED_HTML:
                    MANUAL_EMBED_HTML = MANUAL_EMBED_HTML.replace(pattern, "")
            MANUAL_EMBED_HTML = MANUAL_EMBED_HTML.replace("</body>", f"{script_tag}\n</body>")
        MANUAL_ZIP_BYTES = _build_manual_zip()
        MANUAL_AVAILABLE = True
        MANUAL_URI = HELP_INDEX.as_uri()
    except Exception as exc:
        MANUAL_LOAD_ERROR = f"Failed to load help manual: {exc}"
        MANUAL_EMBED_HTML = ""
else:
    MANUAL_LOAD_ERROR = "Help manual not found at `docs/help/index.html`."
    MANUAL_EMBED_HTML = ""


st.session_state["ui_theme"] = DEFAULT_THEME
st_html("""<script>const prev = document.getElementById('shigley-theme-css'); if (prev && prev.parentNode) { prev.parentNode.removeChild(prev); }</script>""", height=0)
st.markdown(THEME_CSS[DEFAULT_THEME], unsafe_allow_html=True)

with st.sidebar:
    if MANUAL_LOAD_ERROR:
        st.error(
            f"Help manual unavailable: {MANUAL_LOAD_ERROR}. Ensure the documentation files exist in `docs/help/`."
        )
    elif not MANUAL_AVAILABLE:
        st.warning(
            "Help manual unavailable. Ensure the documentation files exist in `docs/help/`."
        )
    else:
        st.caption("The full manual is displayed inside the Help Manual tab.")


def render_print_report(report: dict[str, Any], ui_theme: str) -> None:
    """Expose a client-side print dialog with preformatted problem sections."""
    if not isinstance(report, dict):
        return

    sections: list[str] = []

    def add_section(title: str, content: Any) -> None:
        if _is_empty_payload(content):
            return
        rendered = _content_to_html(content)
        if not rendered:
            return
        sections.append(
            f"<section><h2>{html_lib.escape(title)}</h2>{rendered}</section>"
        )

    add_section("Problem statement", report.get("problem_statement"))
    add_section("Solver class", report.get("solver_class"))
    add_section("Problem inputs", report.get("parsed_inputs") or report.get("input_data"))
    add_section("Requested outputs", report.get("target_outputs"))
    add_section("Assumptions", report.get("assumptions"))
    add_section("Ambiguities", report.get("ambiguities"))
    add_section("Results (SI)", report.get("results"))
    add_section("Formulas and notes", report.get("description"))
    add_section("Solution method", report.get("explanation"))
    add_section("Additional notes", report.get("notes"))

    if not sections:
        return

    report_html = "".join(sections)
    button_styles = {
        DEFAULT_THEME: {
            "background": "linear-gradient(135deg, #2563eb, #8b5cf6)",
            "color": "#f8fafc",
            "border": "none",
            "shadow": "0 12px 28px rgba(37, 99, 235, 0.35)",
            "hover": "0 16px 36px rgba(37, 99, 235, 0.45)",
        },
    }
    style = button_styles.get(ui_theme, button_styles[DEFAULT_THEME])

    button_id = f"print-btn-{uuid.uuid4().hex}"
    component_css = f"""
<style>
.print-report-wrapper {{
  margin-top: 1rem;
  width: 100%;
}}
.print-report-button {{
  background: {style["background"]};
  color: {style["color"]};
  border: {style["border"]};
  border-radius: 8px;
  padding: 0.55rem 1.8rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: {style["shadow"]};
  transition: transform 0.12s ease-in-out, box-shadow 0.12s ease-in-out;
  outline: none;
  border-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
}}
.print-report-button:hover {{
  transform: translateY(-1px);
  box-shadow: {style["hover"]};
}}
.print-report-button:focus {{
  outline: none;
  box-shadow: {style["hover"]};
}}
</style>
"""

    doc_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Problem report</title>
  <script>
    window.MathJax = {
      tex: {
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
      },
      svg: {
        fontCache: 'global'
      }
    };
  </script>
  <style>
    :root {
      color-scheme: only light;
    }
    body {
      font-family: 'Segoe UI', sans-serif;
      background: #ffffff;
      color: #1f2933;
      line-height: 1.6;
      padding: 32px;
    }
    header.report-header {
      border-bottom: 1px solid rgba(148, 163, 184, 0.35);
      margin-bottom: 24px;
      padding-bottom: 16px;
    }
    header.report-header h1 {
      font-size: 28px;
      margin: 0 0 8px 0;
      color: #0f172a;
    }
    header.report-header p {
      margin: 2px 0;
      font-size: 14px;
      color: #475569;
    }
    section {
      margin-bottom: 26px;
    }
    section h2 {
      font-size: 18px;
      margin-bottom: 12px;
      color: #1d4ed8;
    }
    pre {
      background: #f5f7fb;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
    }
    ul {
      padding-left: 22px;
    }
    code {
      background: #edf2ff;
      padding: 0 4px;
      border-radius: 4px;
    }
    .report-text-block {
      white-space: pre-wrap;
      margin-bottom: 12px;
      font-size: 15px;
    }
  </style>
  <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
  <header class="report-header">
    <h1>Problem report</h1>
    <p><strong>Reference:</strong> Shigley's Mechanical Engineering Design</p>
    <p><strong>Creator:</strong> vahid ahmadi khorami</p>
  </header>
  <div id="report-root"></div>
</body>
</html>
"""

    def _js_safe(value: str) -> str:
        """Escape sequences that would prematurely close the enclosing <script> tag."""
        return value.replace("</script>", "<\\/script>")

    report_html_js = _js_safe(json.dumps(report_html, ensure_ascii=False))
    doc_template_js = _js_safe(json.dumps(doc_template, ensure_ascii=False))

    component_script = f"""
<script>
(function() {{
  const reportContent = {report_html_js};
  const docMarkup = {doc_template_js};
  const button = document.getElementById("{button_id}");
  if (!button) {{
    return;
  }}

  button.addEventListener("click", () => {{
    const newWindow = window.open("", "_blank", "width=900,height=680");
    if (!newWindow) {{
      alert("Please allow pop-ups to print the report.");
      return;
    }}

    try {{
      newWindow.document.write(docMarkup);
      newWindow.document.close();
    }} catch (err) {{
      console.error("Failed to prepare report window", err);
      return;
    }}

    const startTime = Date.now();

    const triggerPrint = (win) => {{
      if (!win || win.closed) {{
        return;
      }}
      try {{
        win.focus();
      }} catch (err) {{}}
      try {{
        win.print();
      }} catch (err) {{}}
    }};

    const waitForMathJax = (win) => {{
      if (!win || win.closed) {{
        return;
      }}
      const mathJax = win.MathJax;
      if (mathJax && mathJax.typesetPromise) {{
        mathJax.typesetPromise()
          .then(() => triggerPrint(win))
          .catch(() => triggerPrint(win));
        return;
      }}
      if (Date.now() - startTime > 8000) {{
        triggerPrint(win);
        return;
      }}
      setTimeout(() => waitForMathJax(win), 200);
    }};

    const injectContent = () => {{
      if (!newWindow || newWindow.closed) {{
        return;
      }}
      const target = newWindow.document.getElementById("report-root");
      if (!target) {{
        setTimeout(injectContent, 40);
        return;
      }}
      target.innerHTML = reportContent;
      waitForMathJax(newWindow);
    }};

    injectContent();
  }});
}})();
</script>
"""

    component_html = (
        component_css
        + f'<div class="print-report-wrapper"><button id="{button_id}" '
        + 'class="print-report-button" type="button">Print full report</button></div>'
        + component_script
    )

    st_html(component_html, height=120)


SOLVER_DESCRIPTIONS = {
    "failure.von_mises": r"""
**Purpose:** Evaluate the 3D von Mises equivalent stress and yield safety factor.
- **Inputs:** `stress.{sx, sy, sz, txy, tyz, tzx}` in Pa, `material.S_y`.
- **Formulae:**
  \[
  \sigma_{eq} = \sqrt{\tfrac{1}{2}\left[(\sigma_x-\sigma_y)^2 + (\sigma_y-\sigma_z)^2 + (\sigma_z-\sigma_x)^2\right] + 3(\tau_{xy}^2+\tau_{yz}^2+\tau_{zx}^2)}
  \]
  \[
  n = \frac{S_y}{\sigma_{eq}}
  \]
- **Outputs:** `sigma_eq`, `n_yield`.
""",
    "failure.tresca": r"""
**Purpose:** Apply the Tresca maximum shear stress criterion using principal stresses.
- **Inputs:** `principal.{s1, s2, s3}`, `material.S_y`.
- **Formulae:**
  \[
  \sigma_{eq,T} = \max(|s_1-s_2|, |s_2-s_3|, |s_3-s_1|)
  \]
  \[
  n = \frac{S_y}{\sigma_{eq,T}}
  \]
- **Outputs:** `sigma_eq_tresca`, `n_yield_tresca`.
""",
    "fatigue.endurance_modified": r"""
**Purpose:** Build the modified endurance limit using Marin factors.
- **Inputs:** `material.S_e` or `material.S_e_prime`, factors `marin.{k_a, k_b, k_c, k_d, k_e, k_f}`.
- **Formula:** \( S_e = S'_e \cdot k_a k_b k_c k_d k_e k_f \)
- **Outputs:** `S_e`, detailed factor breakdown.
""",
    "fatigue.goodman": r"""
**Purpose:** Check fatigue safety using the Goodman line for combined alternating/mean stresses.
- **Inputs:** `loads.S_a`, `loads.S_m`, `material.S_ut`, `material.S_e`.
- **Formula:**
  \[
  \frac{S_a}{S_e} + \frac{S_m}{S_{ut}} = \frac{1}{n}
  \]
- **Outputs:** `n_goodman`.
""",
    "fatigue.gerber": r"""
**Purpose:** Evaluate fatigue safety with the Gerber parabola for ductile materials.
- **Inputs:** `loads.S_a`, `loads.S_m`, `material.S_ut`, `material.S_e`.
- **Formula:**
  \[
  \frac{S_a}{S_e} + \left(\frac{S_m}{S_{ut}}\right)^2 = \frac{1}{n}
  \]
- **Outputs:** `n_gerber`.
""",
    "fatigue.soderberg": r"""
**Purpose:** Compute fatigue safety with the linear Soderberg relation (conservative).
- **Inputs:** `loads.S_a`, `loads.S_m`, `material.S_y`, `material.S_e`.
- **Formula:**
  \[
  \frac{S_a}{S_e} + \frac{S_m}{S_y} = \frac{1}{n}
  \]
- **Outputs:** `n_soderberg`.
""",
    "shaft.design.d_required_fatigue": r"""
**Purpose:** Find minimum shaft diameter meeting a target fatigue safety factor.
- **Inputs:** bending/torque amplitudes and means in `loads.*`, material strengths `material.{S_ut, S_y, S_e}`,
  notch and Marin factors in `stress_conc.*`, `notch_sensitivity.*`, `design.*`.
- **Method:** Iterative solve ensuring equivalent alternating/mean stresses satisfy chosen fatigue criterion (modified Goodman) with factors \(K_f = 1 + q_a (K_t - 1)\), \(K_{fs} = 1 + q_s (K_{ts} - 1)\).
- **Outputs:** `d_required`.
""",
    "shaft.design.d_required_static": r"""
**Purpose:** Size a shaft against static yielding under combined bending and torsion.
- **Inputs:** `loads.M`, `loads.T`, `material.S_y`, `stress_conc.{Kt, Kts}`, `factors.{C_b, C_t}`, `design.n`.
- **Formulae:** Using Von Mises on combined stresses with safety \( n \):
  \[
  \sigma = \frac{32 C_b K_t M}{\pi d^3}, \quad \tau = \frac{16 C_t K_{ts} T}{\pi d^3}
  \]
  \[
  \sigma_{eq} = \sqrt{\sigma^2 + 3\tau^2} \le \frac{S_y}{n}
  \]
- **Outputs:** `d_required`.
""",
    "beam.eb.simply_supported.udl": r"""
**Purpose:** Euler-Bernoulli beam analysis for a simply supported beam with uniform distributed load.
- **Inputs:** span `geometry.L`, section (either `I` or {`b`,`h`}), `material.E`, uniform load `loads[q]`.
- **Formulae:**
  \[
  \delta_{mid} = \frac{5 q L^4}{384 E I}, \quad M_{max} = \frac{q L^2}{8}, \quad R = \frac{qL}{2}
  \]
- **Outputs:** `delta_mid`, `M_max`, `R_support`.
""",
    "beam.eb.simply_supported.point_mid": r"""
**Purpose:** Simply supported beam with a central point load.
- **Inputs:** `geometry.L`, section data, `material.E`, point load `loads.P`.
- **Formulae:**
  \[
  \delta_{mid} = \frac{P L^3}{48 E I}, \quad M_{max} = \frac{P L}{4}
  \]
- **Outputs:** `delta_mid`, `M_max`.
""",
    "beam.cantilever.point_end": r"""
**Purpose:** Cantilever beam with an end point load.
- **Inputs:** `geometry.L`, section, `material.E`, load `loads.P`.
- **Formulae:**
  \[
  \delta_{tip} = \frac{P L^3}{3 E I}, \quad M_{max} = P L
  \]
- **Outputs:** `delta_tip`, `M_max`.
""",
    "shaft.torsion.solid": r"""
**Purpose:** Solid circular shaft torsion.
- **Inputs:** `geometry.{L, d}`, `material.G`, `loads.T`.
- **Formulae:**
  \[
  J = \frac{\pi d^4}{32}, \quad \tau_{max} = \frac{16 T}{\pi d^3}, \quad \theta = \frac{T L}{G J}
  \]
- **Outputs:** `tau_max`, `theta`, `J`.
""",
    "shaft.torsion.hollow": r"""
**Purpose:** Hollow circular shaft torsion.
- **Inputs:** `geometry.{L, do, di}`, `material.G`, `loads.T`.
- **Formulae:**
  \[
  J = \frac{\pi (d_o^4 - d_i^4)}{32}, \quad \tau_{max} = \frac{16 T}{\pi d_o^3 (1 - (d_i/d_o)^4)}, \quad \theta = \frac{T L}{G J}
  \]
- **Outputs:** `tau_max`, `theta`, `J`.
""",
    "bolt.preload_proof": r"""
**Purpose:** Recommend bolt preload at proof strength and evaluate clamp reserve.
- **Inputs:** thread area `geometry.A_t`, bolt count `geometry.n`, proof strength `material.S_p`, external load `loads.F_external`.
- **Formulae:** \( F_{pre} = 0.75 A_t S_p \), \( \sigma = F_{pre} / A_t \), reserve \( = n F_{pre} - F_{external} \).
- **Outputs:** `F_pre_per_bolt`, `sigma_at_preload`, `joint_clamp_reserve`.
""",
    "weld.fillet.linear": r"""
**Purpose:** Average shear stress in a straight fillet weld under axial load.
- **Inputs:** throat thickness `geometry.t`, weld length `geometry.Lw`, load `loads.F`.
- **Formula:** \( \tau = \frac{F}{t L_w} \)
- **Outputs:** `tau`.
""",
    "spring.helical.compression": r"""
**Purpose:** Compression coil spring performance.
- **Inputs:** wire diameter `geometry.d`, mean coil diameter `geometry.D`, active turns `geometry.n_a`, shear modulus `material.G`, load `loads.F`.
- **Formulae:**
  \[
  k = \frac{G d^4}{8 n_a D^3}, \quad \delta = \frac{F}{k}, \quad C = \frac{D}{d}, \quad K_s = \frac{4C-1}{4C-4} + \frac{0.615}{C}, \quad \tau_{max} = K_s \frac{8 F D}{\pi d^3}
  \]
- **Outputs:** `k`, `deflection`, `tau_max`, `Wahl_factor`.
""",
    "spring.helical.extension": r"""
**Purpose:** Extension spring with optional initial tension.
- **Inputs:** as compression spring plus `loads.F_initial` or `initial_tension`.
- **Formulae:** same stiffness as compression, working deflection uses \( F - F_i \). Initial extension \( \delta_i = F_i / k \).
- **Outputs:** `k`, `deflection`, `tau_max`, `initial_tension`, `initial_extension`.
""",
    "spring.helical.torsion": r"""
**Purpose:** Helical torsion spring under end moment.
- **Inputs:** `geometry.{d, D, n_a}`, `material.G`, applied moment `loads.M` or `loads.T`.
- **Formulae:**
  \[
  k_\theta = \frac{G d^4}{64 D n_a}, \quad \theta = \frac{M}{k_\theta}, \quad C = \frac{D}{d}, \quad K_b = \frac{4C-1}{4C-4} + \frac{0.615}{C}, \quad \sigma_{max} = K_b \frac{32 M D}{\pi d^3}
  \]
- **Outputs:** `k_theta`, `theta`, `sigma_max`, `Wahl_factor`.
""",
    "spring.helical.parallel": r"""
**Purpose:** Combine two concentric springs acting in parallel.
- **Inputs:** either direct spring rates `springs.spring{1,2}.k` or full geometry/material definitions, total load `loads.F_total`.
- **Formulae:** \( k_{total} = k_1 + k_2 \), deflection \( \delta = F_{total}/k_{total} \), share \( F_i = k_i \delta \).
- **Outputs:** `k_total`, `deflection`, `F_spring1`, `F_spring2`, load sharing.
""",
    "shaft.analysis.segmented": r"""
**Purpose:** Full segmented shaft analysis (bending, torsion, shear, deflection, twist, fatigue).
- **Inputs:** list `segments` (length, diameters), `supports`, `loads` (point, torque, gear, distributed), material properties, optional design-fatigue block.
- **Method:** finite-element-like beam assembly for bending, torsion summation for twist, von Mises combination for critical sections, optional fatigue via modified Goodman.
- **Outputs:** reactions, diagrams (`shear`, `moment`, `torque`, `deflection`), `max_von_mises`, `twist_total`, optional fatigue summary.
""",
    "bearing.ball.L10": r"""
**Purpose:** Estimate basic rating life L10/L10h for rolling bearings.
- **Inputs:** dynamic capacity `catalog.C`, equivalent load `loads.P`, speed `operating.rpm`, optional reliability.
- **Formulae:** \( L_{10} = a_1 \left(\frac{C}{P}\right)^p 10^6 \) revolutions, hours \( = L_{10} / (60 \cdot rpm) \); ball bearings use \( p = 3 \).
- **Outputs:** `L10_rev`, `L10_hours`, `a1`, `p`.
""",
    "bearing.ball.life_reliability": r"""
**Purpose:** Same as L10 but reliability explicitly provided.
- **Inputs/Outputs:** identical to `bearing.ball.L10`.
""",
    "bearing.ball.required_C": r"""
**Purpose:** Compute required dynamic capacity C for a target life/reliability.
- **Inputs:** load `loads.P`, speed `operating.rpm`, life `life.rev` or `life.hours`, reliability `reliability`, exponent `bearing.p`.
- **Formula:** \( C = P \left(\frac{L_{req}}{a_1 10^6}\right)^{1/p} \)
- **Outputs:** `C_required`, `a1`, consistent life figures.
""",
    "bearing.ball.equivalent_load": r"""
**Purpose:** ISO/ABMA equivalent dynamic load for combined radial/axial loads.
- **Inputs:** radial `loads.F_r`, axial `loads.F_a`, coefficients `factors.{V, X, Y, e}`.
- **Formula:** \( P = V X F_r + Y F_a \) when \( F_a/F_r > e \), otherwise \( P = V F_r \).
- **Outputs:** `P_equivalent`, `Fa_over_Fr`, effective coefficients.
""",
    "gear.spur.agma_bending_basic": r"""
**Purpose:** AGMA bending stress for spur gears.
- **Inputs:** tangential load `loads.W_t`, factors `factors.{K_o, K_v, K_s, K_m, K_B}`, geometry `geometry.{J, b, m}`.
- **Formula:** \( \sigma_F = \frac{W_t K_o K_v K_s K_m K_B}{b m} \frac{1}{J} \)
- **Outputs:** `sigma_AGMA_bending`.
""",
    "gear.spur.agma_contact_basic": r"""
**Purpose:** AGMA contact (pitting) stress.
- **Inputs:** `loads.W_t`, factors `factors.{K_o, K_v, K_s, K_m, C_f}`, material factor `material.Z_e`, geometry `geometry.{I, b, d_p}`.
- **Formula:** \( \sigma_H = Z_e \sqrt{\frac{W_t K_o K_v K_s K_m C_f}{b d_p I}} \)
- **Outputs:** `sigma_AGMA_contact`.
""",
    "pv.cylinder.thin": r"""
**Purpose:** Thin-wall pressure vessel stresses.
- **Inputs:** radius `geometry.R`, thickness `geometry.t`, pressure `loads.p`.
- **Formulae:** \( \sigma_{hoop} = \frac{p R}{t} \), \( \sigma_{long} = \frac{p R}{2 t} \).
- **Outputs:** `sigma_hoop`, `sigma_longitudinal`.
""",
    "pv.cylinder.thick": r"""
**Purpose:** Lamé thick-wall cylinder stresses.
- **Inputs:** inner radius `geometry.r_i`, outer radius `geometry.r_o`, pressures `loads.p_i`, `loads.p_o`.
- **Formulae:** define \( A = \frac{p_i r_i^2 - p_o r_o^2}{r_o^2 - r_i^2} \), \( B = \frac{r_i^2 r_o^2 (p_o - p_i)}{r_o^2 - r_i^2} \), then
  \[
  \sigma_r(r) = A - \frac{B}{r^2}, \quad \sigma_t(r) = A + \frac{B}{r^2}
  \]
- **Outputs:** radial and hoop stresses at \( r_i \) and \( r_o \).
""",
    "fit.press.interference": r"""
**Purpose:** Contact pressure for interference fits.
- **Inputs:** shaft radius/modulus/Poisson `shaft.{r_s, E, nu}`, hub dimensions/properties `hub.{r_i, r_o, E, nu}`, radial interference `fit.delta`.
- **Formula:** \( p = \frac{\delta}{C_s + C_h} \) where \( C_s = \frac{1 - \nu_s^2}{E_s r_s} \), \( C_h = \frac{1 - \nu_h^2}{E_h} \frac{r_o^2 + r_i^2}{(r_o^2 - r_i^2) r_i} \).
- **Outputs:** `contact_pressure`.
""",
    "clutch.single_disc.uniform_pressure": r"""
**Purpose:** Torque capacity of a single-disc clutch with uniform pressure.
- **Inputs:** clamp force `loads.F`, friction coefficient `tribology.mu`, radii `geometry.{r_i, r_o}`.
- **Formula:** \( T = \mu F \frac{2}{3} \frac{r_o^3 - r_i^3}{r_o^2 - r_i^2} \)
- **Outputs:** `T`.
""",
    "clutch.single_disc.uniform_wear": r"""
**Purpose:** Torque capacity assuming uniform wear (pressure proportional to 1/r).
- **Inputs:** same as uniform-pressure case.
- **Formula:** \( T = \mu F \frac{r_o + r_i}{2} \)
- **Outputs:** `T`.
""",
    "belt.flat.power": r"""
**Purpose:** Power transmitted by a flat belt.
- **Inputs:** tight/slack tensions `loads.T1`, `loads.T2`, belt speed `operating.v`.
- **Formula:** \( P = (T_1 - T_2) v \)
- **Outputs:** `P`.
""",
    "belt.flat.tension_ratio": r"""
**Purpose:** Compute belt tension ratio using Euler-Eytelwein equation.
- **Inputs:** friction coefficient `tribology.mu`, wrap angle `geometry.theta` (rad).
- **Formula:** \( \frac{T_1}{T_2} = e^{\mu \theta} \)
- **Outputs:** `T1_over_T2`.
""",
    "column.euler": r"""
**Purpose:** Euler buckling for slender columns.
- **Inputs:** modulus `material.E`, second moment `geometry.I`, length `geometry.L`, effective factor `geometry.K`.
- **Formula:** \( P_{cr} = \frac{\pi^2 E I}{(K L)^2} \)
- **Outputs:** `P_cr`.
""",
    "column.johnson": r"""
**Purpose:** Johnson parabolic buckling for intermediate columns.
- **Inputs:** yield strength `material.S_y`, modulus `material.E`, area `geometry.A`, moment `geometry.I`, length `geometry.L`, factor `geometry.K`.
- **Formulae:** radius \( r = \sqrt{I/A} \), slenderness \( \lambda = K L / r \),
  \[
  P_{cr} = A S_y \left[1 - \frac{S_y}{2 \pi^2 E} \lambda^2\right]
  \]
- **Outputs:** `P_cr_johnson`, `slenderness`.
""",
    "power.screw.raise": r"""
**Purpose:** Torque, efficiency, and self-locking for power screws.
- **Inputs:** mean diameter `geometry.d_m`, lead `geometry.lead`, starts `geometry.n_starts`, collar diameter `geometry.d_collar`, friction `tribology.{mu, mu_collar}`, axial load `loads.F`.
- **Formulae:** lead angle \( \alpha = \tan^{-1}(\text{lead}/(\pi d_m)) \), friction angle \( \phi = \tan^{-1}(\mu) \),
  \[
  T_{thread} = \frac{F d_m}{2} \tan(\alpha + \phi), \quad T_{collar} = \frac{F \mu_{collar} d_{collar}}{2}
  \]
  Total raise torque \( T_{total} = T_{thread} + T_{collar} \), efficiency \( \eta = \frac{\tan \alpha}{\tan(\alpha + \phi)} \), self-locking if \( \tan \alpha \le \mu \).
- **Outputs:** thread/collar torques, total torque, helix/fraction angles, efficiency, self-lock flag, optional lowering torque.
""",
}

SOLVER_EXPLANATIONS = {
    "beam.eb.simply_supported.udl": r"""
**Solution outline**

1. Evaluate the section second moment of area \(I\) (either provided directly or computed from rectangular dimensions \(I = \tfrac{b h^3}{12}\)).
2. Resolve support reactions for a uniform load: \(R_A = R_B = \tfrac{qL}{2}\).
3. Compute the maximum bending moment \(M_{max} = \tfrac{qL^2}{8}\) and mid-span deflection \( \delta_{mid} = \tfrac{5 q L^4}{384 E I} \).
4. Report reactions, bending moment, and deflection in SI units.
""",
    "beam.eb.simply_supported.point_mid": r"""
**Solution outline**

1. Confirm the beam span \(L\) and section properties \(I\).
2. Determine reactions for a symmetric point load: \(R_A = R_B = \tfrac{P}{2}\).
3. Evaluate maximum bending moment \(M_{max} = \tfrac{P L}{4}\) at mid-span and deflection \( \delta_{mid} = \tfrac{P L^3}{48 E I} \).
4. Return reactions, deflection, and bending moment for downstream checks.
""",
    "beam.cantilever.point_end": r"""
**Solution outline**

1. Use provided geometry and modulus \(E\) to obtain the section moment of inertia \(I\).
2. The end reaction equals the applied load; the maximum moment occurs at the fixed support: \(M_{max} = P L\).
3. Compute tip deflection \( \delta_{tip} = \tfrac{P L^3}{3 E I} \).
4. Share tip deflection and support moment.
""",
    "shaft.torsion.solid": r"""
**Solution outline**

1. Form the polar moment \( J = \tfrac{\pi d^4}{32} \).
2. Evaluate maximum shear stress \( \tau_{max} = \tfrac{16 T}{\pi d^3} \).
3. Calculate twist angle \( \theta = \tfrac{T L}{G J} \).
4. Present torsional stiffness metrics (shear stress, twist, \(J\)).
""",
    "shaft.torsion.hollow": r"""
**Solution outline**

1. Compute the polar moment for a tube \( J = \tfrac{\pi (d_o^4 - d_i^4)}{32} \).
2. Determine shear stress at the outer fiber \( \tau_{max} = \tfrac{16 T}{\pi d_o^3 (1-(d_i/d_o)^4)} \).
3. Evaluate twist \( \theta = \tfrac{T L}{G J} \).
4. Output stress, twist, and \(J\).
""",
    "shaft.design.d_required_static": r"""
**Solution outline**

1. Assume an initial diameter and compute bending and torsional stresses including concentration factors.
2. Combine stresses via the von Mises criterion \( \sigma_{eq} = \sqrt{\sigma^2 + 3\tau^2} \).
3. Iterate on diameter until \( \sigma_{eq} \leq \tfrac{S_y}{n} \) is satisfied.
4. Report the minimum acceptable diameter meeting the static safety target.
""",
    "shaft.design.d_required_fatigue": r"""
**Solution outline**

1. Convert nominal stresses to fatigue stresses using notch sensitivity: \(K_f = 1 + q_a (K_t - 1)\), \(K_{fs} = 1 + q_s (K_{ts} - 1)\).
2. Compute alternating and mean components in bending/torque and condense via von Mises equivalents.
3. Apply the modified Goodman relation \( \frac{\sigma_a}{S_e} + \frac{\sigma_m}{S_{ut}} = \frac{1}{n} \) with design factor \(n\).
4. Adjust diameter iteratively until the safety requirement is met; return the required shaft size.
""",
    "shaft.analysis.segmented": r"""
**Solution outline**

1. Assemble a piecewise model: convert each segment to stiffness data (second moment \(I\), polar moment \(J\)).
2. Build beam-element stiffness matrices to solve vertical/horizontal deflections and reactions under point, distributed, and gear loads.
3. Integrate torque along the shaft to accumulate twist, then combine bending and torsion to evaluate von Mises stress envelopes.
4. If fatigue data is supplied, compute endurance strength with Marin factors and evaluate safety factors.
5. Return reactions, internal diagrams, peak stresses, twist totals, and optional fatigue assessment.
""",
    "power.screw.raise": r"""
**Solution outline**

1. Derive the lead angle \( \alpha = \tan^{-1}\left(\frac{\text{lead}}{\pi d_m}\right) \) and friction angle \( \phi = \tan^{-1}(\mu) \).
2. Compute thread torque \( T_{thread} = \tfrac{F d_m}{2} \tan(\alpha + \phi) \) and collar torque \( T_{collar} = \tfrac{F \mu_{collar} d_{collar}}{2} \).
3. Sum to total raising torque and determine efficiency \( \eta = \tfrac{\tan \alpha}{\tan(\alpha + \phi)} \).
4. Evaluate self-locking by checking \( \tan \alpha \le \mu \), and, if feasible, compute lowering torque.
""",
    "bearing.ball.L10": r"""
**Solution outline**

1. Normalize reliability input to obtain the ISO factor \( a_1 \).
2. Apply the basic rating life relation \( L_{10} = a_1 (C/P)^p \cdot 10^6 \) revolutions (with exponent \(p = 3\) for ball bearings).
3. Convert to hours \( L_{10h} = \tfrac{L_{10}}{60 \cdot rpm} \).
4. Return rating life in revolutions, hours, and the reliability factor used.
""",
    "bearing.ball.required_C": r"""
**Solution outline**

1. Convert the requested life (hours or revolutions) into total revolutions.
2. Retrieve the reliability factor \( a_1 \) and bearing exponent \(p\).
3. Invert the rating life equation \( C = P \left(\tfrac{L_{req}}{a_1 10^6}\right)^{1/p} \).
4. Report required dynamic capacity and supporting intermediate values.
""",
    "bearing.ball.equivalent_load": r"""
**Solution outline**

1. Form the load ratio \( \frac{F_a}{F_r} \) and compare with threshold \(e\).
2. Select coefficients: if \( \tfrac{F_a}{F_r} \le e\), use \(P = V F_r\); otherwise \(P = V X F_r + Y F_a\).
3. Return equivalent load \(P\) with the ratio and factors that were effective.
""",
    "gear.spur.agma_bending_basic": r"""
**Solution outline**

1. Combine overload, dynamic, size, face load, and rim thickness factors into a single multiplier.
2. Apply the AGMA bending stress expression \( \sigma_F = \tfrac{W_t K_o K_v K_s K_m K_B}{b m J} \).
3. Present the bending stress along with key factors so you can benchmark against allowable stress numbers.
""",
    "gear.spur.agma_contact_basic": r"""
**Solution outline**

1. Multiply the transmitted load by overload, dynamic, size, face load, and surface condition factors.
2. Evaluate the AGMA contact stress \( \sigma_H = Z_e \sqrt{\tfrac{W_t K_o K_v K_s K_m C_f}{b d_p I}} \).
3. Return the contact stress for comparison with pitting resistance limits.
""",
    "pv.cylinder.thin": r"""
**Solution outline**

1. Treat the vessel as thin-walled (\(t \ll R\)) and compute hoop stress \( \sigma_{hoop} = \tfrac{pR}{t} \) and longitudinal stress \( \sigma_{long} = \tfrac{pR}{2t} \).
2. If a yield stress is supplied, compare the dominant stress against it for factor-of-safety insight.
3. Provide membrane stresses for sizing or code checks.
""",
    "pv.cylinder.thick": r"""
**Solution outline**

1. Assume elastic thick-wall behaviour and form Lamé constants \( A \) and \( B \) from the boundary pressures.
2. Evaluate radial stress \( \sigma_r(r) = A - \tfrac{B}{r^2} \) and hoop stress \( \sigma_t(r) = A + \tfrac{B}{r^2} \).
3. Report stresses at inner and outer radii to identify critical locations.
""",
    "fit.press.interference": r"""
**Solution outline**

1. Compute compliances for shaft and hub: \( C_s = \tfrac{1-\nu_s^2}{E_s r_s} \), \( C_h = \tfrac{1-\nu_h^2}{E_h} \tfrac{r_o^2 + r_i^2}{(r_o^2 - r_i^2) r_i} \).
2. Divide interference by combined compliance \( p = \tfrac{\delta}{C_s + C_h} \).
3. Report contact pressure for downstream shear/bearing checks.
""",
    "clutch.single_disc.uniform_pressure": r"""
**Solution outline**

1. Assume constant pressure across the annular contact surface.
2. Integrate frictional shear stress to obtain torque \( T = \mu F \tfrac{2}{3} \tfrac{r_o^3 - r_i^3}{r_o^2 - r_i^2} \).
3. Return torque capacity for comparison with demand torque.
""",
    "clutch.single_disc.uniform_wear": r"""
**Solution outline**

1. Assume wear rate keeps frictional work per unit area constant, yielding a \(1/r\) pressure profile.
2. Integrate to get \( T = \mu F \tfrac{r_o + r_i}{2} \).
3. Present the torque limit and compare with uniform-pressure result if needed.
""",
    "belt.flat.power": r"""
**Solution outline**

1. Take the difference between tight- and slack-side belt tensions.
2. Multiply by belt speed \(v\) to obtain transmitted power \( P = (T_1 - T_2) v \).
3. Provide the power figure in watts for drive sizing.
""",
    "belt.flat.tension_ratio": r"""
**Solution outline**

1. Apply the Euler-Eytelwein relation \( \tfrac{T_1}{T_2} = e^{\mu \theta} \) using wrap angle in radians.
2. Return the tension ratio so you can back-calculate belt tensions from a known load.
""",
    "column.euler": r"""
**Solution outline**

1. Compute the effective length \( L_e = K L \).
2. Evaluate Euler’s critical load \( P_{cr} = \tfrac{\pi^2 E I}{L_e^2} \).
3. Report the buckling load for comparison with applied compressive load.
""",
    "column.johnson": r"""
**Solution outline**

1. Determine radius of gyration \( r = \sqrt{I/A} \) and slenderness \( \lambda = \tfrac{K L}{r} \).
2. Use Johnson’s parabolic expression \( P_{cr} = A S_y \left(1 - \tfrac{S_y}{2 \pi^2 E} \lambda^2\right) \).
3. Share the critical load and slenderness for code check purposes.
""",
    "failure.von_mises": r"""
**Solution outline**

1. Form the deviatoric part of the stress tensor using input components.
2. Evaluate the von Mises scalar per \( \sigma_{eq} \) expression.
3. Divide yield strength by \( \sigma_{eq} \) to obtain factor of safety.
""",
    "failure.tresca": r"""
**Solution outline**

1. Sort principal stresses and compute absolute differences.
2. Take the maximum shear range as equivalent stress.
3. Compare with yield strength to find safety factor.
""",
    "fatigue.endurance_modified": r"""
**Solution outline**

1. Start from the uncorrected endurance limit \( S'_e \) (or convert if only \(S_e\) provided).
2. Multiply by each available Marin factor to account for surface, size, load, temperature, reliability, and miscellany.
3. Return the corrected endurance limit \( S_e \) and factor breakdown to feed subsequent fatigue solvers.
""",
    "fatigue.goodman": r"""
**Solution outline**

1. Normalise alternating stress with respect to \(S_e\) and mean stress with respect to \(S_{ut}\).
2. Sum the ratios as demanded by Goodman’s line.
3. Invert to obtain safety factor \( n = \left(\tfrac{S_a}{S_e} + \tfrac{S_m}{S_{ut}}\right)^{-1} \).
""",
    "fatigue.gerber": r"""
**Solution outline**

1. Form the alternating ratio \(S_a/S_e\).
2. Add the squared mean ratio \( (S_m/S_{ut})^2 \).
3. Invert the sum to obtain Gerber safety factor.
""",
    "fatigue.soderberg": r"""
**Solution outline**

1. Scale alternating stress by \(S_e\) and mean stress by \(S_y\).
2. Sum the ratios (Soderberg line).
3. Take reciprocal to produce the Soderberg safety factor.
""",
    "bearing.ball.life_reliability": r"""
**Solution outline**

Identical to `bearing.ball.L10`, but the user-provided reliability directly controls the \(a_1\) factor before applying the rating life formula.
""",
    "spring.helical.compression": r"""
**Solution outline**

1. Use geometric data to form index \(C\) and stiffness \(k\).
2. Apply Wahl factor to correct shear stress.
3. Report stiffness, deflection under load, maximum shear stress, and correction factor.
""",
    "spring.helical.extension": r"""
**Solution outline**

1. Same stiffness calculations as a compression spring.
2. Deduct initial tension from the applied load when computing working deflection.
3. Provide stiffness, working extension, shear stress, and initial tension metrics.
""",
    "spring.helical.torsion": r"""
**Solution outline**

1. Form torsional spring constant \(k_\theta\).
2. Apply Wahl correction for bending stress in the wire.
3. Output angular deflection, stiffness, and maximum stress.
""",
    "spring.helical.parallel": r"""
**Solution outline**

1. Derive individual spring rates (either directly or from geometry).
2. Sum to obtain total stiffness and compute resulting deflection under the supplied load.
3. Determine how much load each spring carries and report the split.
""",
}


def get_default_json(cls: str) -> str:
    """Return formatted JSON snippet for a solver class."""
    payload = DEFAULT_INPUTS.get(cls, {"geometry": {}, "material": {}, "loads": []})
    return json.dumps(payload, indent=2)


def show_results(
    results: dict,
    solver_class: str | None = None,
    report_meta: dict[str, Any] | None = None,
    ui_theme: str | None = None,
) -> None:
    if not results:
        st.warning("Solver returned no results. Confirm that required inputs are provided.")
        return
    st.subheader("Results (SI units)")
    st.json(results, expanded=False)
    st.download_button(
        "Download results (JSON, SI)",
        data=json.dumps(results, indent=2),
        file_name="solver_results_si.json",
        mime="application/json",
    )
    description_text = ""
    explanation_text = ""

    if solver_class:
        description_raw = SOLVER_DESCRIPTIONS.get(solver_class)
        if description_raw:
            description_text = _format_math(description_raw)
        explanation = SOLVER_EXPLANATIONS.get(solver_class)
        if explanation:
            explanation_text = _format_math(explanation)
            st.subheader("Solution Explanation")
            st.markdown(explanation_text)
        else:
            st.info("No detailed explanation is available for this solver yet.")

    report_payload: dict[str, Any] = {"results": results}
    if solver_class:
        report_payload["solver_class"] = solver_class
    if description_text:
        report_payload["description"] = description_text
    if explanation_text:
        report_payload["explanation"] = explanation_text
    if report_meta:
        report_payload.update(
            {k: v for k, v in report_meta.items() if not _is_empty_payload(v)}
        )

    active_theme = ui_theme or st.session_state.get("ui_theme", DEFAULT_THEME)
    render_print_report(report_payload, active_theme)


# ---------------------------------------------------------------------------
# Streamlit layout
# ---------------------------------------------------------------------------
tab_auto, tab_manual, tab_catalog, tab_help = st.tabs(
    ["Auto Solve from Text", "Manual JSON Inputs", "Solver Catalog", "Help Manual"]
)


# ---- Automatic problem detection & solving --------------------------------
with tab_auto:
    st.caption(
        "Paste an English textbook-style problem. The parser estimates the class, "
        "builds inputs, and invokes the matching solver automatically."
    )
    auto_default = (
        "A simply supported steel beam of span 2 m with a rectangular section 40 mm by 60 mm "
        "carries a uniformly distributed load of 5 kN/m over the entire span. "
        "Take E = 210 GPa. Determine the midspan deflection and the maximum bending stress."
    )
    problem_text = st.text_area(
        "Problem statement",
        auto_default,
        height=220,
        key="auto_problem_text",
    )

    run_auto = st.button("Solve automatically", type="primary", disabled=not problem_text.strip())

    if run_auto and problem_text.strip():
        if not build_spec or not solve_spec:
            st.error("Automatic parser unavailable (builder_core / solver_core not loaded).")
        else:
            spec = build_spec(problem_text)
            st.subheader("Detected class")
            st.write(f"`{spec['class']}` with confidence `{spec['confidence']}`")
            inputs_preview = spec.get("inputs", {})
            st.subheader("Parsed inputs")
            st.json(inputs_preview, expanded=False)
            st.subheader("Outputs requested")
            st.json(spec.get("outputs", []), expanded=False)
            st.subheader("Assumptions & ambiguities")
            c1, c2 = st.columns(2)
            with c1:
                st.json(spec.get("assumptions", []), expanded=False)
            with c2:
                st.json(spec.get("ambiguities", []), expanded=False)

            active_cls = spec.get("class")
            results = solve_spec(spec) if solve_spec else {}

            # Fallback to registry if the parser class already exists there.
            if not results:
                cls = spec.get("class", "")
                aliases = {
                    "column.euler.buckling": "column.euler",
                    "column.johnson": "column.johnson",
                }
                mapped_cls = aliases.get(cls, cls)
                solver_fn = REGISTRY.get(mapped_cls)
                if solver_fn:
                    try:
                        results = solver_fn(inputs_preview)
                        active_cls = mapped_cls
                    except Exception as exc:
                        st.error(f"Manual solver fallback failed: {exc}")

            report_meta = {
                "problem_statement": problem_text.strip(),
                "parsed_inputs": inputs_preview,
                "target_outputs": spec.get("outputs", []),
                "assumptions": spec.get("assumptions", []),
                "ambiguities": spec.get("ambiguities", []),
            }

            show_results(
                results,
                solver_class=active_cls,
                report_meta=report_meta,
                ui_theme=st.session_state.get("ui_theme", DEFAULT_THEME),
            )


# ---- Manual solver workspace ----------------------------------------------
with tab_manual:
    st.caption("Select a solver class, edit the JSON inputs, and run the solver.")
    filter_text = st.text_input("Filter solvers (substring match)", "")
    filtered = [
        cls for cls in AVAILABLE_CLASSES if filter_text.lower() in cls.lower()
    ] or AVAILABLE_CLASSES
    selected_cls = st.selectbox("Solver class", filtered, index=0)
    ta_key = f"manual_input::{selected_cls}"
    if ta_key not in st.session_state:
        st.session_state[ta_key] = get_default_json(selected_cls)

    col_reset, col_doc = st.columns([1, 3])
    with col_reset:
        if st.button("Reset example", key=f"reset::{selected_cls}"):
            st.session_state[ta_key] = get_default_json(selected_cls)
    with col_doc:
        description = SOLVER_DESCRIPTIONS.get(selected_cls)
        if not description:
            fn = REGISTRY[selected_cls]
            description = inspect.getdoc(fn) or "No documentation available."
        st.info(_format_math(description))

    statement_key = f"manual_statement::{selected_cls}"
    if statement_key not in st.session_state:
        st.session_state[statement_key] = ""

    manual_statement = st.text_area(
        "Problem statement / notes (optional, included in printable reports).",
        key=statement_key,
        height=140,
    )

    manual_raw = st.text_area(
        "Inputs JSON (SI values preferred; units accepted via nested dicts).",
        key=ta_key,
        height=320,
    )

    if st.button("Solve selected class", type="primary", key=f"solve::{selected_cls}"):
        try:
            inputs = json.loads(manual_raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - UI validation
            st.error(f"Invalid JSON: {exc}")
        else:
            solver_fn = REGISTRY[selected_cls]
            try:
                results = solver_fn(inputs)
            except Exception as exc:  # pragma: no cover - solver errors
                st.error(f"Solver error: {exc}")
            else:
                report_meta = {
                    "problem_statement": manual_statement.strip(),
                    "input_data": inputs,
                }
                show_results(
                    results,
                    solver_class=selected_cls,
                    report_meta=report_meta,
                    ui_theme=st.session_state.get("ui_theme", DEFAULT_THEME),
                )


# ---- Solver catalog -------------------------------------------------------
with tab_catalog:
    st.markdown(
        """
**Solver Catalog Overview**

Use this reference to understand every registered solver, the assumptions behind it, and the
input data it expects. All quantities are expressed in SI units. Review the notes and equations
for each entry before running a solver to ensure the specification you provide is complete.
"""
    )
    st.divider()
    for cls in AVAILABLE_CLASSES:
        description = SOLVER_DESCRIPTIONS.get(cls)
        if not description:
            fn = REGISTRY[cls]
            description = inspect.getdoc(fn) or "No documentation available."
        st.markdown(f"### `{cls}`")
        st.markdown(_format_math(description.strip()))
        st.divider()


# ---- Help manual -----------------------------------------------------------
with tab_help:
    st.subheader("User manual & help")
    st.write(
        "Access the full help manual directly below for detailed usage instructions, "
        "solver references, and troubleshooting tips."
    )
    if MANUAL_LOAD_ERROR:
        st.error(
            f"Help manual unavailable: {MANUAL_LOAD_ERROR}. Ensure the documentation "
            "files exist in `docs/help/` or regenerate them."
        )
    elif MANUAL_AVAILABLE and MANUAL_EMBED_HTML:
        st_html(MANUAL_EMBED_HTML, height=900, scrolling=True)
    else:
        st.warning(
            "Manual assets are present but could not be rendered inline. Verify file encodings."
        )
