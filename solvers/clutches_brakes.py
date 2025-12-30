
from .common import to_si, ensure
def single_disc_uniform_pressure(inputs):
    F=to_si(inputs.get("loads",{}).get("F")); mu=to_si(inputs.get("tribology",{}).get("mu"),0.35); ri=to_si(inputs.get("geometry",{}).get("r_i")); ro=to_si(inputs.get("geometry",{}).get("r_o"))
    F=ensure(F,"loads.F"); ri=ensure(ri,"geometry.r_i"); ro=ensure(ro,"geometry.r_o")
    T = mu*F*(2.0/3.0)*((ro**3 - ri**3)/(ro**2 - ri**2)); return {"T":T}
def single_disc_uniform_wear(inputs):
    F=to_si(inputs.get("loads",{}).get("F")); mu=to_si(inputs.get("tribology",{}).get("mu"),0.35); ri=to_si(inputs.get("geometry",{}).get("r_i")); ro=to_si(inputs.get("geometry",{}).get("r_o"))
    F=ensure(F,"loads.F"); ri=ensure(ri,"geometry.r_i"); ro=ensure(ro,"geometry.r_o")
    return {"T": mu*F*((ro + ri)/2.0)}
