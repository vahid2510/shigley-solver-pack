import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    yaml = None

from .common import ensure, to_si

_NOTCH_DB_CACHE: Optional[Dict[str, Dict]] = None


def _load_notch_database() -> Dict[str, Dict]:
    """Load and cache notch geometry data from YAML."""
    global _NOTCH_DB_CACHE
    if _NOTCH_DB_CACHE is not None:
        return _NOTCH_DB_CACHE
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for notch lookup in shaft fatigue analysis. "
            "Install PyYAML or omit 'notch_id' in the design.fatigue settings."
        )
    data_path = Path(__file__).resolve().parents[1] / "data" / "notches.yaml"
    try:
        with data_path.open("r", encoding="utf-8") as handle:
            _NOTCH_DB_CACHE = yaml.safe_load(handle) or {}
    except FileNotFoundError as exc:
        raise RuntimeError(f"Notch database not found at {data_path}") from exc
    except Exception as exc:  # pragma: no cover - I/O errors
        raise RuntimeError(f"Failed to load notch database: {exc}") from exc
    return _NOTCH_DB_CACHE


def _section_properties(segment: Dict[str, float]) -> Tuple[float, float, float]:
    d_o = to_si(segment.get("d_o"))
    d_i = to_si(segment.get("d_i"), 0.0)
    d_o = ensure(d_o, "segment.d_o")
    if d_i is None:
        d_i = 0.0
    if d_i < 0 or d_i >= d_o:
        raise ValueError("Invalid inner diameter for shaft segment")
    i = math.pi * (d_o**4 - d_i**4) / 64.0
    j = math.pi * (d_o**4 - d_i**4) / 32.0
    c = d_o / 2.0
    return i, j, c


def _build_geometry(segments: List[Dict[str, float]]) -> List[Dict[str, float]]:
    geom = []
    x = 0.0
    for idx, seg in enumerate(segments):
        length = to_si(seg.get("length"))
        length = ensure(length, f"segments[{idx}].length")
        i, j, c = _section_properties(seg)
        geom.append({
            "start": x,
            "end": x + length,
            "length": length,
            "I": i,
            "J": j,
            "c": c,
            "d_o": to_si(seg.get("d_o")),
            "d_i": to_si(seg.get("d_i"), 0.0)
        })
        x += length
    return geom


def _segment_at(geom: List[Dict[str, float]], x: float) -> Dict[str, float]:
    for seg in geom:
        if seg["start"] - 1e-9 <= x <= seg["end"] + 1e-9:
            return seg
    return geom[-1]


def _collect_loads(loads: List[Dict[str, dict]]) -> Tuple[List[Dict[str, float]], List[Dict[str, float]], float]:
    point_events = []
    distributed = []
    total_torque = 0.0

    for load in loads:
        load_type = load.get("type", "point_force").lower()
        if load_type in ("point", "point_force", "force"):
            x = to_si(load.get("x"))
            if x is None:
                raise ValueError("Point load requires 'x'")
            Fy = to_si(load.get("Fy"), 0.0)
            Fz = to_si(load.get("Fz"), 0.0)
            point_events.append({"x": x, "Fy": Fy, "Fz": Fz, "T": 0.0})
        elif load_type == "torque":
            x = to_si(load.get("x"))
            if x is None:
                raise ValueError("Torque load requires 'x'")
            torque = to_si(load.get("T"))
            point_events.append({"x": x, "Fy": 0.0, "Fz": 0.0, "T": torque})
            total_torque += torque
        elif load_type == "gear":
            x = to_si(load.get("x"))
            radius = to_si(load.get("r"))
            if x is None or radius is None:
                raise ValueError("Gear load requires 'x' and 'r'")
            Ft = to_si(load.get("F_t"), 0.0)
            Fr = to_si(load.get("F_r"), 0.0)
            plane = load.get("radial_plane", "y").lower()
            torque = Ft * radius
            Fy, Fz = 0.0, 0.0
            if plane == "z":
                Fz = Fr
            else:
                Fy = Fr
            point_events.append({"x": x, "Fy": Fy, "Fz": Fz, "T": torque})
            total_torque += torque
        elif load_type in ("distributed", "udl"):
            start = to_si(load.get("start"))
            end = to_si(load.get("end"))
            if start is None or end is None or end <= start:
                raise ValueError("Distributed load requires 'start' < 'end'")
            qy = to_si(load.get("q_y"), 0.0)
            qz = to_si(load.get("q_z"), 0.0)
            q = math.hypot(qy, qz)
            distributed.append({
                "start": start,
                "end": end,
                "q_y": qy,
                "q_z": qz
            })
        elif load_type == "component_weight":
            x = to_si(load.get("x"))
            weight = to_si(load.get("W"))
            if x is None or weight is None:
                raise ValueError("Component weight requires 'x' and 'W'")
            point_events.append({"x": x, "Fy": 0.0, "Fz": -weight, "T": 0.0})
        else:
            raise ValueError(f"Unsupported load type: {load_type}")
    return point_events, distributed, total_torque


def _beam_element_stiffness(EI: float, L: float) -> List[List[float]]:
    L2 = L * L
    L3 = L2 * L
    factor = EI / L3
    return [
        [12.0 * factor, 6.0 * L * factor, -12.0 * factor, 6.0 * L * factor],
        [6.0 * L * factor, 4.0 * L2 * factor, -6.0 * L * factor, 2.0 * L2 * factor],
        [-12.0 * factor, -6.0 * L * factor, 12.0 * factor, -6.0 * L * factor],
        [6.0 * L * factor, 2.0 * L2 * factor, -6.0 * L * factor, 4.0 * L2 * factor],
    ]


def _beam_consistent_load(q: float, L: float) -> List[float]:
    return [q * L / 2.0, q * L**2 / 12.0, q * L / 2.0, -q * L**2 / 12.0]


def _gaussian_solve(matrix: List[List[float]], rhs: List[float]) -> List[float]:
    n = len(rhs)
    A = [row[:] for row in matrix]
    b = rhs[:]
    for i in range(n):
        pivot = i
        max_val = abs(A[i][i])
        for r in range(i + 1, n):
            if abs(A[r][i]) > max_val:
                max_val = abs(A[r][i])
                pivot = r
        if max_val < 1e-12:
            continue
        if pivot != i:
            A[i], A[pivot] = A[pivot], A[i]
            b[i], b[pivot] = b[pivot], b[i]
        pivot_val = A[i][i]
        for j in range(i, n):
            A[i][j] /= pivot_val
        b[i] /= pivot_val
        for r in range(n):
            if r == i:
                continue
            factor = A[r][i]
            if abs(factor) < 1e-12:
                continue
            for c in range(i, n):
                A[r][c] -= factor * A[i][c]
            b[r] -= factor * b[i]
    return b


def _get_float(container: Optional[Dict], key: str, default: Optional[float] = None) -> Optional[float]:
    if not isinstance(container, dict):
        return default
    val = container.get(key)
    if val is None:
        return default
    if isinstance(val, dict):
        return to_si(val)
    return to_si(val)


def _compute_fatigue(design: Dict, material: Dict, critical: Dict) -> Dict:
    fatigue_cfg = design.get("fatigue")
    if not isinstance(fatigue_cfg, dict):
        return {}

    section = critical.get("section", {})
    I = section.get("I")
    J = section.get("J")
    c = section.get("c")
    if not all(v for v in (I, J, c)):
        raise ValueError("Section properties required for fatigue calculation are missing.")

    sigma_b_static = critical.get("sigma_b", 0.0)
    tau_t_static = critical.get("tau_t", 0.0)

    sigma_b_alt = _get_float(fatigue_cfg, "sigma_b_alt", abs(sigma_b_static))
    sigma_b_mean = _get_float(fatigue_cfg, "sigma_b_mean", 0.0)
    tau_t_alt = _get_float(fatigue_cfg, "tau_t_alt", abs(tau_t_static))
    tau_t_mean = _get_float(fatigue_cfg, "tau_t_mean", 0.0)

    M_a = _get_float(fatigue_cfg, "M_a")
    if M_a is not None:
        sigma_b_alt = M_a * c / I
    M_m = _get_float(fatigue_cfg, "M_m")
    if M_m is not None:
        sigma_b_mean = M_m * c / I
    T_a = _get_float(fatigue_cfg, "T_a")
    if T_a is not None:
        tau_t_alt = T_a * c / J
    T_m = _get_float(fatigue_cfg, "T_m")
    if T_m is not None:
        tau_t_mean = T_m * c / J

    Kt = _get_float(fatigue_cfg, "Kt")
    Kts = _get_float(fatigue_cfg, "Kts")

    notch_id = fatigue_cfg.get("notch_id")
    notch_params = fatigue_cfg.get("notch_params")
    if notch_id and isinstance(notch_params, dict):
        try:
            notch_db = _load_notch_database()
        except RuntimeError as exc:
            raise ValueError(str(exc))
        notches = notch_db.get("notches", {})
        if notch_id not in notches:
            raise ValueError(f"Notch id '{notch_id}' not found in notch database.")
        entry = notches[notch_id]
        best = None
        best_metric = float("inf")
        d_small = notch_params.get("d_small")
        d_large = notch_params.get("d_large")
        r = notch_params.get("r")
        if d_small and d_large and d_large > 0 and r and d_small > 0:
            d_over_D = d_small / d_large
            r_over_d = r / d_small
            for candidate in entry.get("data", []):
                metric = abs(candidate.get("d_over_D", 0) - d_over_D) + abs(candidate.get("r_over_d", 0) - r_over_d)
                if metric < best_metric:
                    best_metric = metric
                    best = candidate
        elif notch_id == "groove":
            d = notch_params.get("d")
            w = notch_params.get("groove_width")
            a = notch_params.get("groove_depth")
            r_root = notch_params.get("r_root")
            if d and w and a and r_root:
                w_over_d = w / d
                a_over_d = a / d
                r_over_d = r_root / d
                for candidate in entry.get("data", []):
                    metric = (abs(candidate.get("w_over_d", 0) - w_over_d) +
                              abs(candidate.get("a_over_d", 0) - a_over_d) +
                              abs(candidate.get("r_over_d", 0) - r_over_d))
                    if metric < best_metric:
                        best_metric = metric
                        best = candidate
        if best:
            if Kt is None:
                Kt = best.get("Kt_bending")
            if Kts is None:
                Kts = best.get("Kts_torsion")

    qa = _get_float(fatigue_cfg, "q_a")
    if Kt is None:
        Kf = 1.0
    elif qa is None:
        Kf = Kt
    else:
        Kf = 1.0 + qa * (Kt - 1.0)

    qs = _get_float(fatigue_cfg, "q_s")
    if Kts is None:
        Kfs = 1.0
    elif qs is None:
        Kfs = Kts
    else:
        Kfs = 1.0 + qs * (Kts - 1.0)

    marin = fatigue_cfg.get("marin", {})
    marin_product = 1.0
    marin_components = {}
    for key in ("k_surface", "k_size", "k_load", "k_temp", "k_reliability", "k_misc"):
        val = _get_float(marin, key)
        if val is not None:
            marin_components[key] = val
            marin_product *= val

    S_ut = _get_float(material, "S_ut")
    S_y = _get_float(material, "S_y")
    Se_prime = _get_float(fatigue_cfg, "Se_prime")
    if Se_prime is None and S_ut is not None:
        Se_prime = 0.5 * S_ut
    Se = Se_prime * marin_product if Se_prime is not None else None

    if Se is None or S_ut is None:
        raise ValueError("Endurance limit or ultimate strength is unavailable for fatigue analysis.")

    Kf = max(Kf, 1.0)
    Kfs = max(Kfs, 1.0)

    sigma_a_eq = math.sqrt((Kf * sigma_b_alt)**2 + 3.0 * (Kfs * tau_t_alt)**2)
    sigma_m_eq = math.sqrt((Kf * sigma_b_mean)**2 + 3.0 * (Kfs * tau_t_mean)**2)

    n_goodman = None
    denom_g = (sigma_a_eq / Se) + (sigma_m_eq / S_ut)
    if denom_g > 0:
        n_goodman = 1.0 / denom_g

    n_soderberg = None
    if Se and S_y:
        denom_s = (sigma_a_eq / Se) + (sigma_m_eq / S_y)
        if denom_s > 0:
            n_soderberg = 1.0 / denom_s

    n_asme = None
    if Se and S_y:
        rad = (sigma_a_eq / Se)**2 + (sigma_m_eq / S_y)**2
        if rad > 0:
            n_asme = 1.0 / math.sqrt(rad)

    return {
        "sigma_a_eq": sigma_a_eq,
        "sigma_m_eq": sigma_m_eq,
        "Kf": Kf,
        "Kfs": Kfs,
        "Se": Se,
        "Se_prime": Se_prime,
        "marin_factors": marin_components,
        "n_goodman": n_goodman,
        "n_soderberg": n_soderberg,
        "n_asme": n_asme,
        "sigma_b_alt": sigma_b_alt,
        "sigma_b_mean": sigma_b_mean,
        "tau_t_alt": tau_t_alt,
        "tau_t_mean": tau_t_mean,
        "S_ut": S_ut,
        "S_y": S_y
    }


def shaft_segmented(inputs: Dict) -> Dict:
    segments = inputs.get("segments") or inputs.get("geometry")
    supports = inputs.get("supports", [])
    loads = inputs.get("loads", [])
    material = inputs.get("material", {})
    design = inputs.get("design", {})

    if not segments:
        raise ValueError("Shaft analysis requires 'segments' list with length and diameters.")
    if len(supports) < 2:
        raise ValueError("At least two supports are required for shaft analysis.")

    geom = _build_geometry(segments)
    shaft_length = geom[-1]["end"]

    support_data = []
    for sup in supports:
        x = to_si(sup.get("x"))
        x = ensure(x, "support.x")
        if not (0.0 <= x <= shaft_length + 1e-9):
            raise ValueError("Support position outside shaft length")
        support_data.append({"x": x, "label": sup.get("label", "")})
    supports_sorted = sorted(support_data, key=lambda s: s["x"])

    point_loads, distributed_loads, _ = _collect_loads(loads)

    positions = {0.0, shaft_length}
    for seg in geom:
        positions.add(seg["start"])
        positions.add(seg["end"])
    for sup in supports_sorted:
        positions.add(sup["x"])
    for ld in point_loads:
        positions.add(ld["x"])
    for dist in distributed_loads:
        positions.add(dist["start"])
        positions.add(dist["end"])

    nodes = sorted(positions)
    node_index = {x: idx for idx, x in enumerate(nodes)}
    n_nodes = len(nodes)
    size = 2 * n_nodes

    E = _get_float(material, "E")
    if E is None:
        G = _get_float(material, "G")
        nu = _get_float(material, "nu", 0.3)
        if G is not None:
            E = 2.0 * G * (1.0 + (nu if nu is not None else 0.3))
        else:
            E = 210e9

    Ky = [[0.0 for _ in range(size)] for _ in range(size)]
    Kz = [[0.0 for _ in range(size)] for _ in range(size)]
    Fy = [0.0 for _ in range(size)]
    Fz = [0.0 for _ in range(size)]
    elements = []

    for idx in range(n_nodes - 1):
        xi = nodes[idx]
        xj = nodes[idx + 1]
        L = xj - xi
        if L <= 1e-9:
            continue
        mid = 0.5 * (xi + xj)
        seg = _segment_at(geom, mid)
        EI = E * seg["I"]
        ke = _beam_element_stiffness(EI, L)

        qy = 0.0
        qz = 0.0
        for dist in distributed_loads:
            if dist["start"] <= xi + 1e-9 and dist["end"] >= xj - 1e-9:
                qy += dist["q_y"]
                qz += dist["q_z"]
        fe_y = _beam_consistent_load(qy, L)
        fe_z = _beam_consistent_load(qz, L)

        dofs = [2 * idx, 2 * idx + 1, 2 * (idx + 1), 2 * (idx + 1) + 1]
        for a in range(4):
            for b in range(4):
                Ky[dofs[a]][dofs[b]] += ke[a][b]
                Kz[dofs[a]][dofs[b]] += ke[a][b]
            Fy[dofs[a]] += fe_y[a]
            Fz[dofs[a]] += fe_z[a]

        elements.append({
            "i": idx,
            "j": idx + 1,
            "x_i": xi,
            "x_j": xj,
            "ke": ke,
            "fe_y": fe_y,
            "fe_z": fe_z,
            "geom": seg,
        })

    for ld in point_loads:
        idx = node_index[ld["x"]]
        Fy[2 * idx] += ld["Fy"]
        Fz[2 * idx] += ld["Fz"]

    Ky_orig = [row[:] for row in Ky]
    Kz_orig = [row[:] for row in Kz]
    Fy_orig = Fy[:]
    Fz_orig = Fz[:]

    for sup in supports_sorted:
        idx = node_index[sup["x"]]
        dof = 2 * idx
        for j in range(size):
            Ky[dof][j] = 0.0
            Kz[dof][j] = 0.0
        for i in range(size):
            Ky[i][dof] = 0.0
            Kz[i][dof] = 0.0
        Ky[dof][dof] = 1.0
        Kz[dof][dof] = 1.0
        Fy[dof] = 0.0
        Fz[dof] = 0.0

    disp_y = _gaussian_solve(Ky, Fy)
    disp_z = _gaussian_solve(Kz, Fz)

    reactions_y = [sum(Ky_orig[i][j] * disp_y[j] for j in range(size)) - Fy_orig[i] for i in range(size)]
    reactions_z = [sum(Kz_orig[i][j] * disp_z[j] for j in range(size)) - Fz_orig[i] for i in range(size)]

    node_shear_y = [[] for _ in range(n_nodes)]
    node_moment_y = [[] for _ in range(n_nodes)]
    node_shear_z = [[] for _ in range(n_nodes)]
    node_moment_z = [[] for _ in range(n_nodes)]

    for elem in elements:
        i = elem["i"]
        j = elem["j"]
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]
        d_y = [disp_y[d] for d in dofs]
        d_z = [disp_z[d] for d in dofs]
        ke = elem["ke"]
        fe_y = elem["fe_y"]
        fe_z = elem["fe_z"]
        f_int_y = [sum(ke[a][b] * d_y[b] for b in range(4)) - fe_y[a] for a in range(4)]
        f_int_z = [sum(ke[a][b] * d_z[b] for b in range(4)) - fe_z[a] for a in range(4)]

        node_shear_y[i].append(-f_int_y[0])
        node_moment_y[i].append(-f_int_y[1])
        node_shear_y[j].append(f_int_y[2])
        node_moment_y[j].append(f_int_y[3])

        node_shear_z[i].append(-f_int_z[0])
        node_moment_z[i].append(-f_int_z[1])
        node_shear_z[j].append(f_int_z[2])
        node_moment_z[j].append(f_int_z[3])

    shear_y = []
    shear_z = []
    moment_y = []
    moment_z = []
    for idx, x in enumerate(nodes):
        sy = sum(node_shear_y[idx]) / len(node_shear_y[idx]) if node_shear_y[idx] else 0.0
        sz = sum(node_shear_z[idx]) / len(node_shear_z[idx]) if node_shear_z[idx] else 0.0
        my = sum(node_moment_y[idx]) / len(node_moment_y[idx]) if node_moment_y[idx] else 0.0
        mz = sum(node_moment_z[idx]) / len(node_moment_z[idx]) if node_moment_z[idx] else 0.0
        shear_y.append((x, sy))
        shear_z.append((x, sz))
        moment_y.append((x, my))
        moment_z.append((x, mz))

    torque_points = []
    torque_accum = 0.0
    torque_map = {}
    for ld in point_loads:
        if abs(ld["T"]) > 0:
            torque_map.setdefault(ld["x"], 0.0)
            torque_map[ld["x"]] += ld["T"]
    for x in nodes:
        torque_accum += torque_map.get(x, 0.0)
        torque_points.append((x, torque_accum))

    twist_total = 0.0
    last_x = nodes[0]
    last_T = torque_points[0][1]
    G = _get_float(material, "G", 79e9)
    for idx in range(1, len(nodes)):
        x = nodes[idx]
        L = x - last_x
        if L <= 0:
            continue
        seg = _segment_at(geom, 0.5 * (x + last_x))
        T_here = torque_points[idx][1]
        T_avg = 0.5 * (T_here + last_T)
        twist_total += (T_avg * L) / (G * seg["J"])
        last_T = T_here
        last_x = x

    S_y = to_si(material.get("S_y"))
    S_ut = to_si(material.get("S_ut"))
    if S_y is None and S_ut is not None:
        S_y = S_ut / 1.5
    allowable = S_y if S_y else None

    max_results = {
        "moment": {"value": 0.0, "x": 0.0},
        "shear": {"value": 0.0, "x": 0.0},
        "torque": {"value": 0.0, "x": 0.0},
        "von_mises": {"value": 0.0, "x": 0.0, "sigma_b": 0.0, "tau_t": 0.0},
    }

    for idx, x in enumerate(nodes):
        seg = _segment_at(geom, x)
        My = moment_y[idx][1]
        Mz = moment_z[idx][1]
        M_eq = math.hypot(My, Mz)
        Ty = shear_y[idx][1]
        Tz = shear_z[idx][1]
        V_eq = math.hypot(Ty, Tz)
        T = torque_points[idx][1]

        sigma_b = M_eq * seg["c"] / seg["I"]
        area = math.pi * (seg["d_o"]**2 - seg["d_i"]**2) / 4.0
        tau_shear = V_eq / area if area else 0.0
        tau_t = T * seg["c"] / seg["J"]
        tau_total = math.hypot(tau_shear, tau_t)
        sigma_vm = math.sqrt(sigma_b**2 + 3.0 * tau_total**2)

        if abs(M_eq) > abs(max_results["moment"]["value"]):
            max_results["moment"] = {"value": M_eq, "x": x}
        if abs(V_eq) > abs(max_results["shear"]["value"]):
            max_results["shear"] = {"value": V_eq, "x": x}
        if abs(T) > abs(max_results["torque"]["value"]):
            max_results["torque"] = {"value": T, "x": x}
        if sigma_vm > max_results["von_mises"]["value"]:
            max_results["von_mises"] = {
                "value": sigma_vm,
                "x": x,
                "sigma_b": sigma_b,
                "tau": tau_total,
                "tau_t": tau_t,
                "tau_shear": tau_shear,
                "section": {
                    "d_o": seg["d_o"],
                    "d_i": seg["d_i"],
                    "I": seg["I"],
                    "J": seg["J"],
                    "c": seg["c"]
                }
            }

    fos = None
    if allowable:
        fos = allowable / max_results["von_mises"]["value"] if max_results["von_mises"]["value"] else None

    fatigue_result = None
    if isinstance(design, dict) and design.get("fatigue"):
        try:
            fatigue_result = _compute_fatigue(design, material, max_results["von_mises"])
        except Exception as exc:
            fatigue_result = {"error": str(exc)}

    reactions = []
    for sup in supports_sorted:
        idx = node_index[sup["x"]]
        reactions.append({
            "x": sup["x"],
            "label": sup.get("label", f"R{len(reactions)+1}"),
            "Fy": reactions_y[2 * idx],
            "Fz": reactions_z[2 * idx],
        })

    result = {
        "reactions": reactions,
        "max_moment": max_results["moment"],
        "max_shear": max_results["shear"],
        "max_torque": max_results["torque"],
        "max_von_mises": max_results["von_mises"],
        "fos_yield": fos,
        "twist_total": twist_total,
        "diagrams": {
            "shear_y": shear_y,
            "moment_y": moment_y,
            "shear_z": shear_z,
            "moment_z": moment_z,
            "torque": torque_points,
            "deflection_y": [(x, disp_y[2 * node_index[x]]) for x in nodes],
            "deflection_z": [(x, disp_z[2 * node_index[x]]) for x in nodes],
        }
    }
    if fatigue_result:
        result["fatigue"] = fatigue_result
    return result
