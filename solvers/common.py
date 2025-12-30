
import math
def to_si(q, default=None):
    if isinstance(q, dict):
        if "si" in q:
            try: return float(q["si"])
            except: return default
        if "value" in q:
            try: return float(q["value"])
            except: return default
        return default
    try: return float(q)
    except: return default
def ensure(v, name):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        raise ValueError(f"Missing required input: {name}")
    return v
def I_rect(b, h): return b*h**3/12.0
def S_rect(b, h): return b*h**2/6.0
def lewis_form_factor(N, pressure_angle_deg=20): return 0.154 - 0.912/float(N)
def von_mises_3D(sx, sy, sz, txy, tyz, tzx):
    return math.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2) + 3*(txy**2 + tyz**2 + tzx**2))
def combine_bending_torsion(M, T, d):
    J = math.pi*d**4/32.0; I = math.pi*d**4/64.0; c=d/2.0
    tau = T*c/J; sigma = M*c/I; sigma_eq = (sigma**2 + 3*tau**2)**0.5
    return sigma, tau, sigma_eq
