import math
from typing import Callable, Iterable, Tuple

import pytest

from solvers.registry import REGISTRY

def _approx(actual: float, expected: float, rel: float = 1e-4, abs_tol: float = 1e-9) -> None:
    assert math.isclose(
        actual,
        expected,
        rel_tol=rel,
        abs_tol=max(abs_tol, rel * max(1.0, abs(expected))),
    ), f"{actual} != {expected}"


def _goodman_safety(Ma, Mm, Ta, Tm, d, Kf, Kfs, Se, Sut, n_expected) -> None:
    c = d / 2.0
    I = math.pi * d**4 / 64.0
    J = math.pi * d**4 / 32.0
    sigma_a = 32.0 * Kf * Ma * c / (math.pi * d**4)
    sigma_m = 32.0 * Kf * Mm * c / (math.pi * d**4)
    tau_a = 16.0 * Kfs * Ta * c / (math.pi * d**4)
    tau_m = 16.0 * Kfs * Tm * c / (math.pi * d**4)
    Sa = math.hypot(sigma_a, math.sqrt(3.0) * tau_a)
    Sm = math.hypot(sigma_m, math.sqrt(3.0) * tau_m)
    n = 1.0 / (Sa / Se + Sm / Sut)
    assert n >= n_expected * 0.99  # allow tiny numerical headroom


def _static_shaft_check(d, M, T, Sy, Kt, Kts, n):
    c = d / 2.0
    I = math.pi * d**4 / 64.0
    J = math.pi * d**4 / 32.0
    sigma = Kt * M * c / I
    tau = Kts * T * c / J
    sigma_eq = math.sqrt(sigma**2 + 3 * tau**2)
    assert sigma_eq <= Sy / n * 1.001


def _von_mises_validator(out: dict) -> None:
    sx, sy, sz = 220e6, 80e6, 0.0
    txy = 30e6
    expected = math.sqrt(
        0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy**2)
    )
    _approx(out["sigma_eq"], expected)
    _approx(out["n_yield"], 350e6 / expected)


def _tresca_validator(out: dict) -> None:
    s1, s2, s3 = 250e6, 50e6, -25e6
    seq = max(abs(s1 - s2), abs(s2 - s3), abs(s3 - s1))
    _approx(out["sigma_eq_tresca"], seq)
    _approx(out["n_yield_tresca"], 300e6 / seq)


def _fatigue_endurance_validator(out: dict) -> None:
    _approx(out["S_e"], 600e6 * 0.85 * 0.9 * 1.0 * 0.95 * 1.0 * 0.9)


def _fatigue_goodman_validator(out: dict) -> None:
    _approx(out["n_goodman"], 1.0 / (150e6 / 220e6 + 40e6 / 650e6))


def _fatigue_gerber_validator(out: dict) -> None:
    _approx(out["n_gerber"], 1.0 / (140e6 / 210e6 + (70e6 / 620e6) ** 2))


def _fatigue_soderberg_validator(out: dict) -> None:
    _approx(out["n_soderberg"], 1.0 / (120e6 / 200e6 + 60e6 / 420e6))


def _shaft_static_validator(out: dict) -> None:
    _static_shaft_check(out["d_required"], 2.5e3, 1.5e3, 370e6, 1.5, 1.3, 2.0)


def _shaft_fatigue_validator(out: dict) -> None:
    Kf = 1.0 + 0.85 * (1.4 - 1.0)
    Kfs = 1.0 + 0.9 * (1.2 - 1.0)
    _goodman_safety(
        1.2e3,
        0.5e3,
        0.9e3,
        0.4e3,
        out["d_required"],
        Kf,
        Kfs,
        210e6,
        600e6,
        2.0,
    )


def _beam_udl_validator(out: dict) -> None:
    I = 2.1333333333333334e-06
    _approx(out["delta_mid"], 5 * 4e3 * 2.0**4 / (384 * 200e9 * I))
    _approx(out["M_max"], 4e3 * 2.0**2 / 8.0)
    _approx(out["R_support"], 4e3 * 2.0 / 2.0)


def _beam_point_mid_validator(out: dict) -> None:
    _approx(out["delta_mid"], 12e3 * 3.0**3 / (48 * 210e9 * 3.0e-06))
    _approx(out["M_max"], 12e3 * 3.0 / 4.0)


def _beam_cantilever_validator(out: dict) -> None:
    _approx(out["delta_tip"], 4e3 * 1.5**3 / (3 * 200e9 * 1.5e-06))
    _approx(out["M_max"], 4e3 * 1.5)


def _shaft_solid_validator(out: dict) -> None:
    _approx(out["tau_max"], 16 * 1.2e3 / (math.pi * 0.04**3))
    _approx(out["theta"], 1.2e3 * 0.6 / (80e9 * math.pi * 0.04**4 / 32.0))


def _shaft_hollow_validator(out: dict) -> None:
    _approx(
        out["tau_max"],
        16 * 900.0 / (math.pi * 0.05**3 * (1 - (0.02 / 0.05) ** 4)),
    )
    _approx(
        out["theta"],
        900.0 * 0.5 / (79e9 * math.pi * (0.05**4 - 0.02**4) / 32.0),
    )


def _bolt_validator(out: dict) -> None:
    f_pre = 0.75 * 2.2e-4 * 900e6
    _approx(out["F_pre_per_bolt"], f_pre)
    _approx(out["sigma_at_preload"], f_pre / 2.2e-4)
    _approx(out["joint_clamp_reserve"], 4 * f_pre - 10e3)


def _weld_validator(out: dict) -> None:
    _approx(out["tau"], 12e3 / (0.006 * 0.08))


def _spring_compression_validator(out: dict) -> None:
    k = 79e9 * 0.01**4 / (8 * 8 * 0.08**3)
    _approx(out["k"], k)
    _approx(out["deflection"], 1200.0 / k)


def _spring_extension_validator(out: dict) -> None:
    k = 79e9 * 0.009**4 / (8 * 9 * 0.07**3)
    _approx(out["deflection"], (800.0 - 200.0) / k)
    _approx(out["initial_tension"], 200.0)


def _spring_torsion_validator(out: dict) -> None:
    k_theta = 79e9 * 0.008**4 / (64.0 * 0.06 * 6)
    _approx(out["theta"], 45.0 / k_theta)


def _spring_parallel_validator(out: dict) -> None:
    _approx(out["F_spring1"] + out["F_spring2"], 1500.0)
    _approx(out["deflection"], 1500.0 / out["k_total"])


def _bearing_l10_validator(out: dict) -> None:
    expected = 0.62 * ((25e3 / 4.2e3) ** 3.0) * 1e6
    _approx(out["L10_rev"], expected, rel=1e-3)
    _approx(out["a1"], 0.62, rel=1e-6)


def _bearing_required_c_validator(out: dict) -> None:
    L_rev = 10000.0 * 60 * 1800.0
    expected = 4.2e3 * ((L_rev) / (0.62 * 1e6)) ** (1.0 / 3.0)
    _approx(out["C_required"], expected, rel=1e-3)
    _approx(out["a1"], 0.62, rel=1e-6)


def _bearing_equivalent_load_validator(out: dict) -> None:
    _approx(out["P_equivalent"], 0.56 * 1.0 * 4.0e3 + 1.6 * 1.5e3)
    _approx(out["Fa_over_Fr"], 1.5e3 / 4.0e3)


def _gear_bending_validator(out: dict) -> None:
    _approx(
        out["sigma_AGMA_bending"],
        2200.0 * 1.1 * 1.2 * 1.0 / (0.05 * 0.01) * (1.3 * 1.0 / 0.32),
    )


def _gear_contact_validator(out: dict) -> None:
    _approx(
        out["sigma_AGMA_contact"],
        1890.0
        * math.sqrt((2200.0 * 1.1 * 1.15 * 1.0 * 1.3 / (0.05 * 0.2)) * (1.25 / 0.118)),
    )


def _pv_thin_validator(out: dict) -> None:
    _approx(out["sigma_hoop"], 12e6 * 0.35 / 0.012)
    _approx(out["sigma_longitudinal"], 12e6 * 0.35 / (2 * 0.012))


def _pv_thick_validator(out: dict) -> None:
    ri, ro = 0.1, 0.2
    pi, po = 20e6, 0.0
    A = (pi * ri**2 - po * ro**2) / (ro**2 - ri**2)
    B = (ri**2 * ro**2 * (po - pi)) / (ro**2 - ri**2)
    _approx(out["sigma_t_ri"], A + B / (ri**2))
    _approx(out["sigma_r_ri"], A - B / (ri**2))


def _fit_validator(out: dict) -> None:
    cs = (1 / 210e9) * ((1 - 0.3**2) / 0.05)
    ch = (1 / 200e9) * ((1 - 0.29**2) * (0.09**2 + 0.05**2) / ((0.09**2 - 0.05**2) * 0.05))
    _approx(out["contact_pressure"], 30e-6 / (cs + ch))


def _clutch_pressure_validator(out: dict) -> None:
    _approx(out["T"], 0.32 * 14e3 * (2.0 / 3.0) * ((0.12**3 - 0.07**3) / (0.12**2 - 0.07**2)))


def _clutch_wear_validator(out: dict) -> None:
    _approx(out["T"], 0.3 * 12e3 * ((0.11 + 0.06) / 2.0))


def _belt_power_validator(out: dict) -> None:
    _approx(out["P"], (1.6e3 - 0.6e3) * 12.0)


def _belt_ratio_validator(out: dict) -> None:
    _approx(out["T1_over_T2"], math.e ** (0.3 * math.pi / 2))


def _column_euler_validator(out: dict) -> None:
    _approx(out["P_cr"], (math.pi**2) * 210e9 * 8.5e-6 / ((0.7 * 2.2) ** 2))


def _column_johnson_validator(out: dict) -> None:
    r = math.sqrt(8.5e-6 / 4.5e-4)
    _approx(out["P_cr_johnson"], 4.5e-4 * 350e6 * (1.0 - (350e6 / (2.0 * math.pi**2 * 210e9)) * (((0.75 * 1.8) / r) ** 2)))
    _approx(out["slenderness"], (0.75 * 1.8) / r)


def _power_screw_validator(out: dict) -> None:
    _approx(out["T_total_raise"], out["T_thread_raise"] + out["T_collar"])
    _approx(out["efficiency"], math.tan(out["helix_angle"]) / math.tan(out["helix_angle"] + out["friction_angle"]))
    assert out["self_locking"] is True


SAMPLE_CASES: Iterable[Tuple[str, dict, Callable[[dict], None]]] = [
    (
        "failure.von_mises",
        {
            "stress": {"sx": 220e6, "sy": 80e6, "txy": 30e6},
            "material": {"S_y": 350e6},
        },
        _von_mises_validator,
    ),
    (
        "failure.tresca",
        {
            "principal": {"s1": 250e6, "s2": 50e6, "s3": -25e6},
            "material": {"S_y": 300e6},
        },
        _tresca_validator,
    ),
    (
        "fatigue.endurance_modified",
        {
            "material": {"S_e_prime": 600e6},
            "marin": {"k_a": 0.85, "k_b": 0.9, "k_c": 1.0, "k_d": 0.95, "k_e": 1.0, "k_f": 0.9},
        },
        _fatigue_endurance_validator,
    ),
    (
        "fatigue.goodman",
        {
            "loads": {"S_a": 150e6, "S_m": 40e6},
            "material": {"S_ut": 650e6, "S_e": 220e6},
        },
        _fatigue_goodman_validator,
    ),
    (
        "fatigue.gerber",
        {
            "loads": {"S_a": 140e6, "S_m": 70e6},
            "material": {"S_ut": 620e6, "S_e": 210e6},
        },
        _fatigue_gerber_validator,
    ),
    (
        "fatigue.soderberg",
        {
            "loads": {"S_a": 120e6, "S_m": 60e6},
            "material": {"S_y": 420e6, "S_e": 200e6},
        },
        _fatigue_soderberg_validator,
    ),
    (
        "shaft.design.d_required_static",
        {
            "loads": {"M": 2.5e3, "T": 1.5e3},
            "material": {"S_y": 370e6},
            "design": {"n": 2.0},
            "stress_conc": {"Kt": 1.5, "Kts": 1.3},
            "factors": {"C_b": 1.0, "C_t": 1.0},
        },
        _shaft_static_validator,
    ),
    (
        "shaft.design.d_required_fatigue",
        {
            "loads": {"M_a": 1.2e3, "M_m": 0.5e3, "T_a": 0.9e3, "T_m": 0.4e3},
            "material": {"S_ut": 600e6, "S_y": 360e6, "S_e": 210e6},
            "design": {"n": 2.0},
            "stress_conc": {"Kt": 1.4, "Kts": 1.2},
            "notch_sensitivity": {"q_a": 0.85, "q_s": 0.9},
        },
        _shaft_fatigue_validator,
    ),
    (
        "beam.eb.simply_supported.udl",
        {
            "geometry": {"L": 2.0, "section": {"I": 2.1333333333333334e-06}},
            "material": {"E": 200e9},
            "loads": [{"type": "uniform", "q": 4e3}],
        },
        _beam_udl_validator,
    ),
    (
        "beam.eb.simply_supported.point_mid",
        {
            "geometry": {"L": 3.0, "section": {"I": 3.0e-06}},
            "material": {"E": 210e9},
            "loads": [{"type": "point", "at": "mid", "P": 12e3}],
        },
        _beam_point_mid_validator,
    ),
    (
        "beam.cantilever.point_end",
        {
            "geometry": {"L": 1.5, "section": {"I": 1.5e-06}},
            "material": {"E": 200e9},
            "loads": [{"type": "point", "at": "free", "P": 4e3}],
        },
        _beam_cantilever_validator,
    ),
    (
        "shaft.torsion.solid",
        {
            "geometry": {"L": 0.6, "d": 0.04},
            "material": {"G": 80e9},
            "loads": {"T": 1.2e3},
        },
        _shaft_solid_validator,
    ),
    (
        "shaft.torsion.hollow",
        {
            "geometry": {"L": 0.5, "do": 0.05, "di": 0.02},
            "material": {"G": 79e9},
            "loads": {"T": 900.0},
        },
        _shaft_hollow_validator,
    ),
    (
        "bolt.preload_proof",
        {
            "geometry": {"A_t": 2.2e-4, "n": 4},
            "material": {"S_p": 900e6},
            "loads": {"F_external": 10e3},
        },
        _bolt_validator,
    ),
    (
        "weld.fillet.linear",
        {
            "geometry": {"t": 0.006, "Lw": 0.08},
            "loads": {"F": 12e3},
        },
        _weld_validator,
    ),
    (
        "spring.helical.compression",
        {
            "geometry": {"d": 0.01, "D": 0.08, "n_a": 8},
            "material": {"G": 79e9},
            "loads": {"F": 1200.0},
        },
        _spring_compression_validator,
    ),
    (
        "spring.helical.extension",
        {
            "geometry": {"d": 0.009, "D": 0.07, "n_a": 9},
            "material": {"G": 79e9},
            "loads": {"F": 800.0, "F_initial": 200.0},
        },
        _spring_extension_validator,
    ),
    (
        "spring.helical.torsion",
        {
            "geometry": {"d": 0.008, "D": 0.06, "n_a": 6},
            "material": {"G": 79e9},
            "loads": {"M": 45.0},
        },
        _spring_torsion_validator,
    ),
    (
        "spring.helical.parallel",
        {
            "springs": {
                "spring1": {"geometry": {"d": 0.009, "D": 0.07, "n_a": 9}, "material": {"G": 79e9}},
                "spring2": {"geometry": {"d": 0.01, "D": 0.09, "n_a": 8}, "material": {"G": 79e9}},
            },
            "loads": {"F_total": 1500.0},
        },
        _spring_parallel_validator,
    ),
    (
        "bearing.ball.L10",
        {
            "catalog": {"C": 25e3},
            "loads": {"P": 4.2e3},
            "operating": {"rpm": 1800.0},
            "reliability": {"percent": 95.0},
            "bearing": {"p": 3.0},
        },
        _bearing_l10_validator,
    ),
    (
        "bearing.ball.life_reliability",
        {
            "catalog": {"C": 25e3},
            "loads": {"P": 4.2e3},
            "operating": {"rpm": 1800.0},
            "reliability": {"R": 0.95},
            "bearing": {"p": 3.0},
        },
        _bearing_l10_validator,
    ),
    (
        "bearing.ball.required_C",
        {
            "loads": {"P": 4.2e3},
            "operating": {"rpm": 1800.0},
            "life": {"hours": 10000.0},
            "reliability": {"percent": 95.0},
            "bearing": {"p": 3.0},
        },
        _bearing_required_c_validator,
    ),
    (
        "bearing.ball.equivalent_load",
        {
            "loads": {"F_r": 4.0e3, "F_a": 1.5e3},
            "factors": {"V": 1.0, "X": 0.56, "Y": 1.6, "e": 0.3},
        },
        _bearing_equivalent_load_validator,
    ),
    (
        "gear.spur.agma_bending_basic",
        {
            "loads": {"W_t": 2200.0},
            "factors": {"K_o": 1.1, "K_v": 1.2, "K_s": 1.0, "K_m": 1.3, "K_B": 1.0},
            "geometry": {"J": 0.32, "b": 0.05, "m": 0.01},
        },
        _gear_bending_validator,
    ),
    (
        "gear.spur.agma_contact_basic",
        {
            "loads": {"W_t": 2200.0},
            "factors": {"K_o": 1.1, "K_v": 1.15, "K_s": 1.0, "K_m": 1.3, "C_f": 1.25},
            "material": {"Z_e": 1890.0},
            "geometry": {"I": 0.118, "b": 0.05, "d_p": 0.2},
        },
        _gear_contact_validator,
    ),
    (
        "pv.cylinder.thin",
        {
            "geometry": {"R": 0.35, "t": 0.012},
            "loads": {"p": 12e6},
        },
        _pv_thin_validator,
    ),
    (
        "pv.cylinder.thick",
        {
            "geometry": {"r_i": 0.1, "r_o": 0.2},
            "loads": {"p_i": 20e6, "p_o": 0.0},
        },
        _pv_thick_validator,
    ),
    (
        "fit.press.interference",
        {
            "shaft": {"r_s": 0.05, "E": 210e9, "nu": 0.3},
            "hub": {"r_i": 0.05, "r_o": 0.09, "E": 200e9, "nu": 0.29},
            "fit": {"delta": 30e-6},
        },
        _fit_validator,
    ),
    (
        "clutch.single_disc.uniform_pressure",
        {
            "loads": {"F": 14e3},
            "tribology": {"mu": 0.32},
            "geometry": {"r_i": 0.07, "r_o": 0.12},
        },
        _clutch_pressure_validator,
    ),
    (
        "clutch.single_disc.uniform_wear",
        {
            "loads": {"F": 12e3},
            "tribology": {"mu": 0.3},
            "geometry": {"r_i": 0.06, "r_o": 0.11},
        },
        _clutch_wear_validator,
    ),
    (
        "belt.flat.power",
        {
            "loads": {"T1": 1.6e3, "T2": 0.6e3},
            "operating": {"v": 12.0},
        },
        _belt_power_validator,
    ),
    (
        "belt.flat.tension_ratio",
        {
            "tribology": {"mu": 0.3},
            "geometry": {"theta": math.pi / 2},
        },
        _belt_ratio_validator,
    ),
    (
        "column.euler",
        {
            "material": {"E": 210e9},
            "geometry": {"I": 8.5e-6, "L": 2.2, "K": 0.7},
        },
        _column_euler_validator,
    ),
    (
        "column.johnson",
        {
            "material": {"E": 210e9, "S_y": 350e6},
            "geometry": {"A": 4.5e-4, "I": 8.5e-6, "L": 1.8, "K": 0.75},
        },
        _column_johnson_validator,
    ),
    (
        "power.screw.raise",
        {
            "geometry": {"d_m": 0.036, "lead": 0.006, "d_collar": 0.06},
            "tribology": {"mu": 0.15, "mu_collar": 0.08},
            "loads": {"F": 25e3},
        },
        _power_screw_validator,
    ),
]


@pytest.mark.parametrize("class_key,inputs,validator", SAMPLE_CASES)
def test_registry_samples(class_key: str, inputs: dict, validator: Callable[[dict], None]) -> None:
    result = REGISTRY[class_key](inputs)
    assert isinstance(result, dict)
    validator(result)


def test_shafts_segmented_smoke():
    inputs = {
        "segments": [
            {"length": 0.3, "d_o": 0.05},
            {"length": 0.2, "d_o": 0.04},
        ],
        "supports": [{"x": 0.0, "label": "A"}, {"x": 0.5, "label": "B"}],
        "loads": [
            {"type": "point", "x": 0.3, "Fy": -2000.0},
            {"type": "torque", "x": 0.5, "T": 400.0},
        ],
        "material": {"E": 210e9, "G": 80e9},
    }
    out = REGISTRY["shaft.analysis.segmented"](inputs)
    assert "reactions" in out and len(out["reactions"]) == 2
    assert out["max_moment"]["value"] > 0.0
    assert out["max_von_mises"]["value"] >= 0.0
    assert out["twist_total"] >= 0.0
