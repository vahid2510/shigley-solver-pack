
from .common import to_si, ensure, von_mises_3D
def von_mises(inputs):
    sx=to_si(inputs.get("stress",{}).get("sx")); sy=to_si(inputs.get("stress",{}).get("sy"),0.0)
    sz=to_si(inputs.get("stress",{}).get("sz"),0.0); txy=to_si(inputs.get("stress",{}).get("txy"),0.0)
    tyz=to_si(inputs.get("stress",{}).get("tyz"),0.0); tzx=to_si(inputs.get("stress",{}).get("tzx"),0.0)
    Sy=to_si(inputs.get("material",{}).get("S_y")); sx=ensure(sx,"stress.sx"); Sy=ensure(Sy,"material.S_y")
    seq = von_mises_3D(sx,sy,sz,txy,tyz,tzx); n = Sy/seq if seq>0 else float("inf")
    return {"sigma_eq": seq, "n_yield": n}
def tresca(inputs):
    s1=to_si(inputs.get("principal",{}).get("s1")); s2=to_si(inputs.get("principal",{}).get("s2"),0.0); s3=to_si(inputs.get("principal",{}).get("s3"),0.0)
    Sy=to_si(inputs.get("material",{}).get("S_y")); s1=ensure(s1,"principal.s1"); Sy=ensure(Sy,"material.S_y")
    seq=max(abs(s1-s2),abs(s2-s3),abs(s3-s1)); n=Sy/seq if seq>0 else float("inf"); return {"sigma_eq_tresca":seq,"n_yield_tresca":n}
