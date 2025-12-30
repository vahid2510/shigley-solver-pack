
import math
from .common import to_si, ensure
def diameter_static(inputs):
    M=to_si(inputs.get("loads",{}).get("M")); T=to_si(inputs.get("loads",{}).get("T"))
    Sy=to_si(inputs.get("material",{}).get("S_y")); n=to_si(inputs.get("design",{}).get("n"),2.0)
    Kt=to_si(inputs.get("stress_conc",{}).get("Kt"),1.0); Kts=to_si(inputs.get("stress_conc",{}).get("Kts"),1.0)
    Cb=to_si(inputs.get("factors",{}).get("C_b"),1.0); Ct=to_si(inputs.get("factors",{}).get("C_t"),1.0)
    M=ensure(M,"loads.M"); T=ensure(T,"loads.T"); Sy=ensure(Sy,"material.S_y")
    def ok(d):
        I=math.pi*d**4/64.0; J=math.pi*d**4/32.0; c=d/2.0
        sigma = Cb*Kt*(M*c/I); tau = Ct*Kts*(T*c/J); sigma_eq=(sigma**2 + 3*tau**2)**0.5
        return sigma_eq <= Sy/n
    lo,hi=1e-4,0.5
    for _ in range(80):
        mid=(lo+hi)/2.0
        if ok(mid): hi=mid
        else: lo=mid
    return {"d_required":hi}
