import math

from .common import ensure, to_si


def raising_torque(F: float, d_m: float, lead: float, mu: float) -> float:
    """Torque needed to raise the load (square thread assumption)."""
    if d_m <= 0.0 or lead <= 0.0:
        raise ValueError("Mean diameter and lead must be positive.")
    alpha = math.atan(lead / (math.pi * d_m))
    phi = math.atan(mu)
    return F * d_m / 2.0 * math.tan(alpha + phi)


def lowering_torque(F: float, d_m: float, lead: float, mu: float) -> float:
    """Torque that would be delivered as the load descends (useful for self-lock checks)."""
    if d_m <= 0.0 or lead <= 0.0:
        raise ValueError("Mean diameter and lead must be positive.")
    alpha = math.atan(lead / (math.pi * d_m))
    phi = math.atan(mu)
    return F * d_m / 2.0 * math.tan(alpha - phi)


def power_screw(inputs):
    geom = inputs.get("geometry", {})
    loads = inputs.get("loads", {})
    trib = inputs.get("tribology", {})

    F = ensure(to_si(loads.get("F")), "loads.F")
    lead = to_si(geom.get("lead"))
    pitch = to_si(geom.get("pitch"))
    n_starts = geom.get("n_starts") or geom.get("starts") or 1
    if isinstance(n_starts, dict):
        n_starts = to_si(n_starts)
    try:
        n_starts = int(n_starts)
    except Exception:
        n_starts = 1
    if lead is None and pitch is not None:
        lead = pitch * max(1, n_starts)
    lead = ensure(lead, "geometry.lead")

    d_m = geom.get("d_m") or geom.get("diameter_mean") or geom.get("mean_diameter")
    d_m = ensure(to_si(d_m), "geometry.d_m")

    mu_val = trib.get("mu")
    mu = to_si(mu_val) if isinstance(mu_val, dict) else mu_val
    mu = 0.15 if mu is None else float(mu)
    mu_c_val = trib.get("mu_collar", trib.get("mu_c"))
    mu_c = to_si(mu_c_val) if isinstance(mu_c_val, dict) else mu_c_val if mu_c_val is not None else 0.0
    mu_c = float(mu_c)

    d_c = geom.get("d_collar") or geom.get("collar_diameter") or geom.get("d_c")
    d_c = to_si(d_c) if d_c is not None else 0.0

    alpha = math.atan(lead / (math.pi * d_m))
    phi = math.atan(mu)

    T_thread_raise = raising_torque(F, d_m, lead, mu)
    T_collar = F * mu_c * d_c / 2.0 if d_c and mu_c else 0.0
    T_total_raise = T_thread_raise + T_collar

    try:
        T_thread_lower = lowering_torque(F, d_m, lead, mu)
    except ValueError:
        T_thread_lower = None

    efficiency = math.tan(alpha) / math.tan(alpha + phi)
    self_locking = abs(math.tan(alpha)) <= mu

    result = {
        "helix_angle": alpha,
        "friction_angle": phi,
        "T_thread_raise": T_thread_raise,
        "T_collar": T_collar,
        "T_total_raise": T_total_raise,
        "efficiency": efficiency,
        "self_locking": self_locking,
        "lead": lead,
        "starts": n_starts,
    }
    if T_thread_lower is not None:
        result["T_thread_lower"] = T_thread_lower
        if T_collar:
            result["T_total_lower"] = T_thread_lower - T_collar
    return result
