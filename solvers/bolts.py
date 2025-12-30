from .common import to_si, ensure

def preload_proof(inputs):
    At=to_si(inputs.get("geometry",{}).get("A_t"))
    Sp=to_si(inputs.get("material",{}).get("S_p"))
    n=inputs.get("geometry",{}).get("n") or 1
    Fext=to_si(inputs.get("loads",{}).get("F_external"),0.0)
    At=ensure(At,"geometry.A_t"); Sp=ensure(Sp,"material.S_p")
    Fpre=0.75*At*Sp; sigma=Fpre/At; reserve=n*Fpre - Fext
    return {"F_pre_per_bolt":Fpre,"sigma_at_preload":sigma,"joint_clamp_reserve":reserve}
