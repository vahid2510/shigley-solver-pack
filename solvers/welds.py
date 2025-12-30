from .common import to_si, ensure

def fillet_linear(inputs):
    t=to_si(inputs.get("geometry",{}).get("t")); Lw=to_si(inputs.get("geometry",{}).get("Lw")); F=to_si(inputs.get("loads",{}).get("F"))
    t=ensure(t,"geometry.t"); Lw=ensure(Lw,"geometry.Lw"); F=ensure(F,"loads.F")
    Aw=t*Lw; tau=F/Aw; return {"tau":tau}
