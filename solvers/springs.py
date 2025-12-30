import math
from .common import to_si, ensure


def _wahl_factor(C: float) -> float:
    return ((4.0 * C - 1.0) / (4.0 * C - 4.0)) + 0.615 / C


def helical_compression(inputs):
    geom = inputs.get("geometry", {})
    material = inputs.get("material", {})
    loads = inputs.get("loads", {})

    d = ensure(to_si(geom.get("d")), "geometry.d")
    D = ensure(to_si(geom.get("D")), "geometry.D")
    na = ensure(to_si(geom.get("n_a")), "geometry.n_a")
    G = ensure(to_si(material.get("G")), "material.G")
    F = ensure(to_si(loads.get("F")), "loads.F")

    k = (G * d**4) / (8.0 * na * D**3)
    delta = F / k
    C = D / d
    Ks = _wahl_factor(C)
    tau = Ks * (8.0 * F * D) / (math.pi * d**3)
    return {"k": k, "deflection": delta, "tau_max": tau, "Wahl_factor": Ks}


def helical_extension(inputs):
    geom = inputs.get("geometry", {})
    material = inputs.get("material", {})
    loads = inputs.get("loads", {})

    d = ensure(to_si(geom.get("d")), "geometry.d")
    D = ensure(to_si(geom.get("D")), "geometry.D")
    na = ensure(to_si(geom.get("n_a")), "geometry.n_a")
    G = ensure(to_si(material.get("G")), "material.G")
    F = ensure(to_si(loads.get("F")), "loads.F")
    Fi = to_si(loads.get("F_initial")) if isinstance(loads, dict) else None
    if Fi is None:
        Fi = to_si(inputs.get("initial_tension"))  # legacy field

    k = (G * d**4) / (8.0 * na * D**3)
    delta_working = max(0.0, (F - Fi) / k) if Fi else F / k
    C = D / d
    Ks = _wahl_factor(C)
    tau = Ks * (8.0 * F * D) / (math.pi * d**3)
    result = {
        "k": k,
        "deflection": delta_working,
        "tau_max": tau,
        "Wahl_factor": Ks,
    }
    if Fi:
        result["initial_tension"] = Fi
        result["initial_extension"] = Fi / k
    return result


def helical_torsion(inputs):
    geom = inputs.get("geometry", {})
    material = inputs.get("material", {})
    loads = inputs.get("loads", {})

    d = ensure(to_si(geom.get("d")), "geometry.d")
    D = ensure(to_si(geom.get("D")), "geometry.D")
    na = ensure(to_si(geom.get("n_a")), "geometry.n_a")
    G = ensure(to_si(material.get("G")), "material.G")
    M = loads.get("M")
    if M is None:
        M = loads.get("T")
    M = ensure(to_si(M), "loads.M")

    C = D / d
    Kb = _wahl_factor(C)
    k_theta = (G * d**4) / (64.0 * D * na)
    theta = M / k_theta
    sigma = Kb * (32.0 * M * D) / (math.pi * d**3)
    return {"k_theta": k_theta, "theta": theta, "sigma_max": sigma, "Wahl_factor": Kb}


def concentric_parallel(inputs):
    springs = inputs.get("springs", {})
    load_data = inputs.get("loads", {})
    F_total = ensure(to_si(load_data.get("F_total")), "loads.F_total")

    def spring_rate(data, label):
        if data is None:
            raise ValueError(f"Missing {label} configuration")
        if "k" in data:
            return to_si(data["k"])
        geom = data.get("geometry", {})
        material = data.get("material", {})
        d = ensure(to_si(geom.get("d")), f"{label}.geometry.d")
        D = ensure(to_si(geom.get("D")), f"{label}.geometry.D")
        na = ensure(to_si(geom.get("n_a")), f"{label}.geometry.n_a")
        G = ensure(to_si(material.get("G")), f"{label}.material.G")
        return (G * d**4) / (8.0 * na * D**3)

    k1 = spring_rate(springs.get("spring1"), "spring1")
    k2 = spring_rate(springs.get("spring2"), "spring2")
    k_eq = k1 + k2
    delta = F_total / k_eq
    F1 = k1 * delta
    F2 = k2 * delta
    share1 = F1 / F_total if F_total else 0.0
    return {
        "k_total": k_eq,
        "deflection": delta,
        "F_spring1": F1,
        "F_spring2": F2,
        "load_share_spring1": share1,
        "load_share_spring2": 1.0 - share1,
    }
