
from .common import to_si, ensure, I_rect
def simply_supported_udl(inputs):
    L=to_si(inputs.get("geometry",{}).get("L")); E=to_si(inputs.get("material",{}).get("E"))
    sec=inputs.get("geometry",{}).get("section",{}); I=to_si(sec.get("I"))
    if I is None and "b" in sec and "h" in sec: I=I_rect(to_si(sec["b"]), to_si(sec["h"]))
    q=None
    for ld in inputs.get("loads",[]):
        if ld.get("type")=="uniform": q=to_si(ld.get("q")); break
    L=ensure(L,"geometry.L"); E=ensure(E,"material.E"); I=ensure(I,"geometry.section.I"); q=ensure(q,"loads.q")
    delta=5*q*L**4/(384*E*I); M=q*L**2/8.0; R=q*L/2.0
    return {"delta_mid":delta,"M_max":M,"R_support":R}
def cantilever_point_end(inputs):
    L=to_si(inputs.get("geometry",{}).get("L")); E=to_si(inputs.get("material",{}).get("E"))
    sec=inputs.get("geometry",{}).get("section",{}); I=to_si(sec.get("I"))
    if I is None and "b" in sec and "h" in sec: I=I_rect(to_si(sec["b"]), to_si(sec["h"]))
    P=None
    for ld in inputs.get("loads",[]):
        if ld.get("type")=="point" and ld.get("at") in ("free","x=L"): P=to_si(ld.get("P")); break
    L=ensure(L,"geometry.L"); E=ensure(E,"material.E"); I=ensure(I,"geometry.section.I"); P=ensure(P,"loads.P")
    return {"delta_tip": P*L**3/(3*E*I), "M_max": P*L}
def simply_supported_point_mid(inputs):
    L=to_si(inputs.get("geometry",{}).get("L")); E=to_si(inputs.get("material",{}).get("E"))
    sec=inputs.get("geometry",{}).get("section",{}); I=to_si(sec.get("I"))
    if I is None and "b" in sec and "h" in sec: I=I_rect(to_si(sec["b"]), to_si(sec["h"]))
    P=None
    for ld in inputs.get("loads",[]):
        if ld.get("type")=="point" and ld.get("at") in ("mid","x=L/2"): P=to_si(ld.get("P")); break
    L=ensure(L,"geometry.L"); E=ensure(E,"material.E"); I=ensure(I,"geometry.section.I"); P=ensure(P,"loads.P")
    return {"delta_mid": P*L**3/(48*E*I), "M_max": P*L/4.0}
