from .common import to_si, ensure

A1_TABLE = [
    (0.90, 1.00),
    (0.95, 0.62),
    (0.96, 0.53),
    (0.97, 0.44),
    (0.98, 0.33),
    (0.99, 0.21),
]


def _normalize_reliability(val):
    if val is None:
        return None
    try:
        val = float(val)
    except (TypeError, ValueError):
        return None
    if val > 1.0:
        val = val / 100.0
    return max(0.5, min(0.999, val))


def reliability_factor(R):
    R = _normalize_reliability(R)
    if R is None or R <= 0.90:
        return 1.0
    if R >= 0.99:
        return 0.21
    for (r1, a1), (r2, a2) in zip(A1_TABLE, A1_TABLE[1:]):
        if r1 <= R <= r2:
            span = r2 - r1
            frac = (R - r1) / span if span > 0 else 0.0
            return a1 + frac * (a2 - a1)
    return 1.0


def _bearing_life(C, P, rpm, R=None, p_exp=3.0):
    a1 = reliability_factor(R)
    L10_rev = (a1 * ((C / P) ** p_exp)) * 1e6
    L10_hours = L10_rev / (60.0 * rpm) if rpm else None
    return {"L10_rev": L10_rev, "L10_hours": L10_hours, "a1": a1}


def L10(inputs):
    catalog = inputs.get("catalog", {})
    loads = inputs.get("loads", {})
    operating = inputs.get("operating", {})
    reliability = inputs.get("reliability", {})
    bearing_data = inputs.get("bearing", {})

    C = ensure(to_si(catalog.get("C")), "catalog.C")
    P = ensure(to_si(loads.get("P")), "loads.P")
    rpm = ensure(to_si(operating.get("rpm")), "operating.rpm")
    R = reliability.get("R", reliability.get("percent"))
    if isinstance(R, dict):
        R = R.get("si", R.get("value"))
    p_exp = to_si(bearing_data.get("p")) if isinstance(bearing_data.get("p"), dict) else bearing_data.get("p", 3.0)
    if not isinstance(p_exp, (int, float)):
        p_exp = 3.0
    result = _bearing_life(C, P, rpm, R, p_exp)
    result["p"] = p_exp
    result["P"] = P
    return result


def life_with_reliability(inputs):
    return L10(inputs)


def required_rating(inputs):
    loads = inputs.get("loads", {})
    operating = inputs.get("operating", {})
    life = inputs.get("life", {})
    reliability = inputs.get("reliability", {})
    bearing_data = inputs.get("bearing", {})

    P = ensure(to_si(loads.get("P")), "loads.P")
    rpm = to_si(operating.get("rpm"))
    L_rev = to_si(life.get("rev"))
    L_hours = life.get("hours")

    if isinstance(L_hours, dict):
        L_hours = L_hours.get("si", L_hours.get("value"))
    if L_rev is None and L_hours is not None:
        rpm = ensure(rpm, "operating.rpm")
        L_rev = L_hours * 60.0 * rpm
    L_rev = ensure(L_rev, "life.rev or life.hours")

    R = reliability.get("R", reliability.get("percent"))
    if isinstance(R, dict):
        R = R.get("si", R.get("value"))
    p_exp = to_si(bearing_data.get("p")) if isinstance(bearing_data.get("p"), dict) else bearing_data.get("p", 3.0)
    if not isinstance(p_exp, (int, float)):
        p_exp = 3.0

    a1 = reliability_factor(R)
    C_required = P * ((L_rev / (a1 * 1e6)) ** (1.0 / p_exp))
    return {"C_required": C_required, "a1": a1, "P": P, "p": p_exp}


def equivalent_dynamic_load(inputs):
    loads = inputs.get("loads", {})
    factors = inputs.get("factors", {})

    Fr = ensure(to_si(loads.get("F_r")), "loads.F_r")
    Fa = to_si(loads.get("F_a"), 0.0)
    V = to_si(factors.get("V"), 1.0)
    X = to_si(factors.get("X"), 1.0)
    Y = to_si(factors.get("Y"), 0.0)
    e_val = to_si(factors.get("e"))

    ratio = (Fa / Fr) if Fr else 0.0
    if e_val is not None and ratio <= e_val:
        Y_eff = 0.0
        X_eff = 1.0
    else:
        X_eff = X
        Y_eff = Y
    P = X_eff * V * Fr + Y_eff * Fa
    return {"P_equivalent": P, "Fa_over_Fr": ratio, "X_used": X_eff, "Y_used": Y_eff, "V": V}
