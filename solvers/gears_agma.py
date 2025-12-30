
import math
from .common import to_si, ensure
def spur_bending_basic(inputs):
    Wt=to_si(inputs.get("loads",{}).get("W_t")); Ko=to_si(inputs.get("factors",{}).get("K_o"),1.0); Kv=to_si(inputs.get("factors",{}).get("K_v"),1.0)
    Ks=to_si(inputs.get("factors",{}).get("K_s"),1.0); Km=to_si(inputs.get("factors",{}).get("K_m"),1.0); Kb=to_si(inputs.get("factors",{}).get("K_B"),1.0)
    J=to_si(inputs.get("geometry",{}).get("J")); b=to_si(inputs.get("geometry",{}).get("b")); m=to_si(inputs.get("geometry",{}).get("m"))
    for name,val in [("W_t",Wt),("J",J),("b",b),("m",m)]: ensure(val,name)
    sigma=Wt*Ko*Kv*Ks/(b*m) * (Km*Kb/J); return {"sigma_AGMA_bending":sigma}
def spur_contact_basic(inputs):
    Wt=to_si(inputs.get("loads",{}).get("W_t")); Ko=to_si(inputs.get("factors",{}).get("K_o"),1.0); Kv=to_si(inputs.get("factors",{}).get("K_v"),1.0)
    Ks=to_si(inputs.get("factors",{}).get("K_s"),1.0); Km=to_si(inputs.get("factors",{}).get("K_m"),1.0); Ze=to_si(inputs.get("material",{}).get("Z_e"))
    Cf=to_si(inputs.get("factors",{}).get("C_f"),1.0); I=to_si(inputs.get("geometry",{}).get("I")); b=to_si(inputs.get("geometry",{}).get("b")); dp=to_si(inputs.get("geometry",{}).get("d_p"))
    for name,val in [("W_t",Wt),("Z_e",Ze),("I",I),("b",b),("d_p",dp)]: ensure(val,name)
    sc=Ze*math.sqrt((Wt*Ko*Kv*Ks*Km/(b*dp))*(Cf/I)); return {"sigma_AGMA_contact":sc}
