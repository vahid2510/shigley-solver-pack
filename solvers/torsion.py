
import math
from .common import to_si, ensure
def solid(inputs):
    T=to_si(inputs.get("loads",{}).get("T")); L=to_si(inputs.get("geometry",{}).get("L"))
    G=to_si(inputs.get("material",{}).get("G")); d=to_si(inputs.get("geometry",{}).get("d"))
    T=ensure(T,"loads.T"); L=ensure(L,"geometry.L"); G=ensure(G,"material.G"); d=ensure(d,"geometry.d")
    J=math.pi*d**4/32.0; tau=16*T/(math.pi*d**3); theta=T*L/(G*J); return {"tau_max":tau,"theta":theta,"J":J}
def hollow(inputs):
    T=to_si(inputs.get("loads",{}).get("T")); L=to_si(inputs.get("geometry",{}).get("L"))
    G=to_si(inputs.get("material",{}).get("G")); do=to_si(inputs.get("geometry",{}).get("do")); di=to_si(inputs.get("geometry",{}).get("di"))
    T=ensure(T,"loads.T"); L=ensure(L,"geometry.L"); G=ensure(G,"material.G"); do=ensure(do,"geometry.do"); di=ensure(di,"geometry.di")
    J=math.pi*(do**4 - di**4)/32.0; tau=16*T/(math.pi*do**3*(1-(di/do)**4)); theta=T*L/(G*J); return {"tau_max":tau,"theta":theta,"J":J}
