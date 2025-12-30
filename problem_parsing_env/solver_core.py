
# solver_core.py — Deterministic solvers for Phase‑1 classes
import math

try:
    from solvers import springs as _springs, torsion as _torsion, bearings as _bearings, shaft_analysis as _shaft, power_screw as _power_screw, clutches_brakes as _clutches, belts as _belts
except ImportError:
    _springs = None
    _torsion = None
    _bearings = None
    _shaft = None
    _power_screw = None
    _clutches = None
    _belts = None

# --- Unit helpers ---
def to_si(q):
    """Return SI value from quantity dict with 'si' field; fallback to value if missing."""
    if isinstance(q, dict):
        if "si" in q:
            try:
                return float(q["si"])
            except (TypeError, ValueError):
                pass
        if "value" in q:
            try:
                return float(q["value"])
            except (TypeError, ValueError):
                pass
        return None
    return float(q) if q is not None else None

def need(d, key, default=None):
    return d.get(key, default) if isinstance(d, dict) else default

def derive_I_rect(b_si, h_si):
    # I = b*h^3/12 (about strong axis)
    return b_si * (h_si**3) / 12.0

# Unit formatting (very small subset for display)
def fmt(value_si, unit_pref):
    conv = 1.0
    if unit_pref is None:
        return value_si
    u = unit_pref.lower()
    if u == "mm":
        conv = 1e3
    elif u == "m":
        conv = 1.0
    elif u == "mpa":
        conv = 1e-6  # Pa -> MPa
    elif u == "pa":
        conv = 1.0
    elif u == "n":
        conv = 1.0
    elif u == "kn":
        conv = 1e-3
    elif u == "n·m" or u == "n*m":
        conv = 1.0
    elif u == "hz":
        conv = 1.0
    elif u == "s":
        conv = 1.0
    else:
        conv = 1.0
    return value_si * conv

def solve_beam_udl(spec):
    inp = spec.get("inputs", {})
    geom = inp.get("geometry", {})
    material = inp.get("material", {})
    loads = inp.get("loads", [])

    L = to_si(geom.get("L"))
    E = to_si(need(material, "E", {}))
    # Section & I
    sec = need(geom, "section", {})
    I = None
    if "I" in sec:
        I = to_si(sec["I"])
    else:
        b = need(sec, "b", {}); h = need(sec, "h", {})
        if b and h:
            I = derive_I_rect(to_si(b), to_si(h))
    # Load q
    q = None
    for ld in loads:
        if ld.get("type") == "uniform":
            q = to_si(need(ld, "q", {}))
            break

    results_si = {}
    if all(v is not None for v in [L, E, I, q]):
        # Midspan deflection: δ = 5 q L^4 / (384 E I)
        delta_mid = 5.0 * q * (L**4) / (384.0 * E * I)
        # Max bending stress: σ_max = M_max * c / I, with M_max = q L^2 / 8, c = h/2 if known
        Mmax = q * (L**2) / 8.0
        h = to_si(need(sec, "h", {}))
        if h is not None:
            c = h / 2.0
            sigma_max = Mmax * c / I  # Pa
        else:
            sigma_max = None
        results_si["deflection_mid"] = delta_mid
        if sigma_max is not None:
            results_si["sigma_bending_max"] = sigma_max
        # Reactions at each support for UDL over full span
        R = q * L / 2.0
        results_si["reaction_left"] = R
        results_si["reaction_right"] = R

    return results_si

def solve_pv_cylinder(spec):
    inp = spec.get("inputs", {})
    geom = inp.get("geometry", {}); material = inp.get("material", {}); loads = inp.get("loads", [])

    R = to_si(geom.get("R"))
    t = to_si(geom.get("t"))
    p = None
    for ld in loads:
        if ld.get("type") == "pressure":
            p = to_si(need(ld, "p", {}))
            break
    sigma_y = to_si(need(material, "sigma_y", {}))

    results_si = {}
    if all(v is not None for v in [R, t, p]):
        sigma_hoop = p * R / t
        sigma_long = p * R / (2.0 * t)
        results_si["sigma_hoop"] = sigma_hoop
        results_si["sigma_longitudinal"] = sigma_long
        if sigma_y is not None and sigma_y > 0:
            results_si["fos_yield"] = sigma_y / max(sigma_hoop, sigma_long)
    return results_si

def solve_column_buckling(spec):
    inp = spec.get("inputs", {})
    geom = inp.get("geometry", {}); material = inp.get("material", {})

    E = to_si(need(material, "E", {}))
    I = to_si(need(geom, "I", {}))
    L = to_si(need(geom, "L", {}))
    K = need(geom, "K", None)
    K = to_si(K) if isinstance(K, dict) else (K if K is not None else 1.0)

    results_si = {}
    if all(v is not None for v in [E, I, L, K]):
        Pcr = (math.pi**2) * E * I / ((K * L)**2)
        results_si["P_cr"] = Pcr
    return results_si

def solve_sdof_base(spec):
    """Computes natural frequency and relative displacement amplitude under harmonic base acceleration.
       Note: x_peak is relative amplitude; absolute displacement requires vector sum with base motion.
    """
    inp = spec.get("inputs", {})
    sys = inp.get("system", {}); exc = inp.get("excitation", {})

    m = to_si(sys.get("m"))
    k = to_si(sys.get("k"))
    zeta = to_si(sys.get("zeta")) if isinstance(sys.get("zeta"), dict) else sys.get("zeta")
    a0 = to_si(exc.get("a0"))
    f = to_si(exc.get("f"))

    results_si = {}
    if m and k:
        wn = math.sqrt(k/m)           # rad/s
        fn = wn/(2.0*math.pi)         # Hz
        T = 1.0/fn if fn>0 else None
        results_si["fn"] = fn
        if T is not None: results_si["T"] = T
        if a0 and f:
            w = 2.0*math.pi*f
            r = w/wn
            if zeta is None: zeta = 0.02
            # Relative displacement amplitude X_rel from base displacement Y=A0/w^2:
            # |X_rel| = |Y| * ( r^2 / sqrt((1 - r^2)^2 + (2ζr)^2) ), with |Y| = a0 / w^2
            H = (r**2) / math.sqrt((1.0 - r**2)**2 + (2.0*zeta*r)**2)
            Xrel = (a0 / (w**2)) * H
            results_si["x_peak"] = Xrel  # meters (relative)
    return results_si

def solve_spring_helical(spec):
    if _springs is None:
        return {}
    try:
        return _springs.helical_compression(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_spring_extension(spec):
    if _springs is None:
        return {}
    try:
        return _springs.helical_extension(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_spring_torsion(spec):
    if _springs is None:
        return {}
    try:
        return _springs.helical_torsion(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_spring_parallel(spec):
    if _springs is None:
        return {}
    try:
        return _springs.concentric_parallel(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_bearing_life(spec):
    if _bearings is None:
        return {}
    try:
        return _bearings.life_with_reliability(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_bearing_required(spec):
    if _bearings is None:
        return {}
    try:
        return _bearings.required_rating(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_bearing_equivalent(spec):
    if _bearings is None:
        return {}
    try:
        return _bearings.equivalent_dynamic_load(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_shaft_segmented(spec):
    if _shaft is None:
        return {}
    try:
        return _shaft.shaft_segmented(spec.get("inputs", {}))
    except Exception:
        return {}

def solve_torsion_solid(spec):
    if _torsion is None:
        return {}
    try:
        return _torsion.solid(spec.get("inputs", {}))
    except Exception:
        return {}


def solve_power_screw(spec):
    if _power_screw is None:
        return {}
    try:
        return _power_screw.power_screw(spec.get("inputs", {}))
    except Exception:
        return {}


def solve_clutch_uniform_wear(spec):
    if _clutches is None:
        return {}
    try:
        return _clutches.single_disc_uniform_wear(spec.get("inputs", {}))
    except Exception:
        return {}


def solve_clutch_uniform_pressure(spec):
    if _clutches is None:
        return {}
    try:
        return _clutches.single_disc_uniform_pressure(spec.get("inputs", {}))
    except Exception:
        return {}


def solve_belt_power(spec):
    if _belts is None:
        return {}
    try:
        return _belts.flat_belt_power(spec.get("inputs", {}))
    except Exception:
        return {}


def solve_belt_tension_ratio(spec):
    if _belts is None:
        return {}
    try:
        return _belts.tension_ratio(spec.get("inputs", {}))
    except Exception:
        return {}

def solve(spec):
    cls = spec.get("class","")
    if cls == "beam.eb.simply_supported.udl":
        return solve_beam_udl(spec)
    if cls == "pv.cylinder.thin":
        return solve_pv_cylinder(spec)
    if cls == "column.euler.buckling":
        return solve_column_buckling(spec)
    if cls == "bearing.ball.L10":
        return solve_bearing_life(spec)
    if cls == "bearing.ball.life_reliability":
        return solve_bearing_life(spec)
    if cls == "bearing.ball.required_C":
        return solve_bearing_required(spec)
    if cls == "bearing.ball.equivalent_load":
        return solve_bearing_equivalent(spec)
    if cls == "spring.helical.compression":
        return solve_spring_helical(spec)
    if cls == "spring.helical.extension":
        return solve_spring_extension(spec)
    if cls == "spring.helical.torsion":
        return solve_spring_torsion(spec)
    if cls == "spring.helical.parallel":
        return solve_spring_parallel(spec)
    if cls == "shaft.analysis.segmented":
        return solve_shaft_segmented(spec)
    if cls == "shaft.torsion.solid":
        return solve_torsion_solid(spec)
    if cls in ("power.screw", "power.screw.raise"):
        return solve_power_screw(spec)
    if cls == "clutch.single_disc.uniform_wear":
        return solve_clutch_uniform_wear(spec)
    if cls == "clutch.single_disc.uniform_pressure":
        return solve_clutch_uniform_pressure(spec)
    if cls == "belt.flat.power":
        return solve_belt_power(spec)
    if cls == "belt.flat.tension_ratio":
        return solve_belt_tension_ratio(spec)
    if cls == "dyn.sdof.base_excited.harmonic":
        return solve_sdof_base(spec)
    return {}
