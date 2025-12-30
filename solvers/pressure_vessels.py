
from .common import to_si, ensure
def thin_cylinder(inputs):
    R=to_si(inputs.get("geometry",{}).get("R")); t=to_si(inputs.get("geometry",{}).get("t")); p=to_si(inputs.get("loads",{}).get("p"))
    R=ensure(R,"geometry.R"); t=ensure(t,"geometry.t"); p=ensure(p,"loads.p")
    return {"sigma_hoop": p*R/t, "sigma_longitudinal": p*R/(2*t)}
def thick_cylinder_lame(inputs):
    ri=to_si(inputs.get("geometry",{}).get("r_i")); ro=to_si(inputs.get("geometry",{}).get("r_o")); pi=to_si(inputs.get("loads",{}).get("p_i")); po=to_si(inputs.get("loads",{}).get("p_o"),0.0)
    ri=ensure(ri,"geometry.r_i"); ro=ensure(ro,"geometry.r_o"); pi=ensure(pi,"loads.p_i")
    A=(pi*ri**2 - po*ro**2)/(ro**2 - ri**2); B=(ri**2*ro**2*(po - pi))/(ro**2 - ri**2)
    return {"sigma_r_ri": A - B/(ri**2), "sigma_t_ri": A + B/(ri**2),
            "sigma_r_ro": A - B/(ro**2), "sigma_t_ro": A + B/(ro**2)}
