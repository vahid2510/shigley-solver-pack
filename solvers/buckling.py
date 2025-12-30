
import math
from .common import to_si, ensure
def euler(inputs):
    E=to_si(inputs.get("material",{}).get("E")); I=to_si(inputs.get("geometry",{}).get("I")); L=to_si(inputs.get("geometry",{}).get("L")); K=to_si(inputs.get("geometry",{}).get("K"),1.0)
    E=ensure(E,"material.E"); I=ensure(I,"geometry.I"); L=ensure(L,"geometry.L")
    return {"P_cr": (math.pi**2)*E*I/((K*L)**2)}
def johnson_parabolic(inputs):
    Sy=to_si(inputs.get("material",{}).get("S_y")); E=to_si(inputs.get("material",{}).get("E")); A=to_si(inputs.get("geometry",{}).get("A")); I=to_si(inputs.get("geometry",{}).get("I"))
    L=to_si(inputs.get("geometry",{}).get("L")); K=to_si(inputs.get("geometry",{}).get("K"),1.0)
    Sy=ensure(Sy,"material.S_y"); E=ensure(E,"material.E"); A=ensure(A,"geometry.A"); I=ensure(I,"geometry.I"); L=ensure(L,"geometry.L")
    r=(I/A)**0.5; P = A*Sy*(1.0 - (Sy/(2.0*math.pi**2*E))*((K*L/r)**2) ); return {"P_cr_johnson":P,"slenderness":(K*L)/r}
