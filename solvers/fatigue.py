
import math
from .common import to_si, ensure, combine_bending_torsion
def endurance_modified(inputs):
    Se=to_si(inputs.get("material",{}).get("S_e"))
    if Se is not None: return {"S_e":Se}
    Se0=to_si(inputs.get("material",{}).get("S_e_prime"))
    ka=to_si(inputs.get("marin",{}).get("k_a"),1.0); kb=to_si(inputs.get("marin",{}).get("k_b"),1.0)
    kc=to_si(inputs.get("marin",{}).get("k_c"),1.0); kd=to_si(inputs.get("marin",{}).get("k_d"),1.0)
    ke=to_si(inputs.get("marin",{}).get("k_e"),1.0); kf=to_si(inputs.get("marin",{}).get("k_f"),1.0)
    if Se0 is None: raise ValueError("Need S_e or S_e_prime + Marin factors")
    Se=Se0*ka*kb*kc*kd*ke*kf; return {"S_e":Se,"factors":{"k_a":ka,"k_b":kb,"k_c":kc,"k_d":kd,"k_e":ke,"k_f":kf}}
def goodman(inputs):
    Sa=to_si(inputs.get("loads",{}).get("S_a")); Sm=to_si(inputs.get("loads",{}).get("S_m"))
    Sut=to_si(inputs.get("material",{}).get("S_ut")); Se=to_si(inputs.get("material",{}).get("S_e"))
    Sa=ensure(Sa,"loads.S_a"); Sm=ensure(Sm,"loads.S_m"); Sut=ensure(Sut,"material.S_ut"); Se=ensure(Se,"material.S_e")
    n=1.0/(Sa/Se + Sm/Sut); return {"n_goodman":n}
def soderberg(inputs):
    Sa=to_si(inputs.get("loads",{}).get("S_a")); Sm=to_si(inputs.get("loads",{}).get("S_m"))
    Sy=to_si(inputs.get("material",{}).get("S_y")); Se=to_si(inputs.get("material",{}).get("S_e"))
    Sa=ensure(Sa,"loads.S_a"); Sm=ensure(Sm,"loads.S_m"); Sy=ensure(Sy,"material.S_y"); Se=ensure(Se,"material.S_e")
    n=1.0/(Sa/Se + Sm/Sy); return {"n_soderberg":n}
def gerber(inputs):
    Sa=to_si(inputs.get("loads",{}).get("S_a")); Sm=to_si(inputs.get("loads",{}).get("S_m"))
    Sut=to_si(inputs.get("material",{}).get("S_ut")); Se=to_si(inputs.get("material",{}).get("S_e"))
    Sa=ensure(Sa,"loads.S_a"); Sm=ensure(Sm,"loads.S_m"); Sut=ensure(Sut,"material.S_ut"); Se=ensure(Se,"material.S_e")
    invn = Sa/Se + (Sm/Sut)**2; n = 1.0/invn if invn>0 else float("inf"); return {"n_gerber":n}
def shaft_required_d(inputs):
    Ma=to_si(inputs.get("loads",{}).get("M_a"),0.0); Mm=to_si(inputs.get("loads",{}).get("M_m"),0.0)
    Ta=to_si(inputs.get("loads",{}).get("T_a"),0.0); Tm=to_si(inputs.get("loads",{}).get("T_m"),0.0)
    Sut=to_si(inputs.get("material",{}).get("S_ut")); Sy=to_si(inputs.get("material",{}).get("S_y"),Sut/1.5 if Sut else None); Se=to_si(inputs.get("material",{}).get("S_e"))
    n=to_si(inputs.get("design",{}).get("n"),2.0)
    if Se is None: raise ValueError("Need material.S_e")
    Kt=to_si(inputs.get("stress_conc",{}).get("Kt"),1.0); Kts=to_si(inputs.get("stress_conc",{}).get("Kts"),1.0)
    qa=to_si(inputs.get("notch_sensitivity",{}).get("q_a"),1.0); qs=to_si(inputs.get("notch_sensitivity",{}).get("q_s"),1.0)
    Kf=1.0 + qa*(Kt-1.0); Kfs=1.0 + qs*(Kts-1.0)
    import math
    def eq_vm(sig, tau): return (sig*sig + 3*tau*tau)**0.5
    def safety(d):
        sig_a=32*Kf*Ma/(math.pi*d**3); tau_a=16*Kfs*Ta/(math.pi*d**3)
        sig_m=32*Kf*Mm/(math.pi*d**3); tau_m=16*Kfs*Tm/(math.pi*d**3)
        Sa=eq_vm(sig_a,tau_a); Sm=eq_vm(sig_m,tau_m); invn=Sa/Se + Sm/Sut; return 1.0/invn if invn>0 else float("inf")
    lo,hi=1e-4,0.5
    for _ in range(80):
        mid=(lo+hi)/2.0
        if safety(mid)>=n: hi=mid
        else: lo=mid
    return {"d_required":hi}
