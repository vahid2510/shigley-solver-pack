
from .common import to_si, ensure
def press_fit(inputs):
    rs=to_si(inputs.get("shaft",{}).get("r_s")); Es=to_si(inputs.get("shaft",{}).get("E")); nus=to_si(inputs.get("shaft",{}).get("nu"),0.3)
    ri=to_si(inputs.get("hub",{}).get("r_i")); ro=to_si(inputs.get("hub",{}).get("r_o")); Eh=to_si(inputs.get("hub",{}).get("E")); nuh=to_si(inputs.get("hub",{}).get("nu"),0.3)
    delta=to_si(inputs.get("fit",{}).get("delta"))
    rs=ensure(rs,"shaft.r_s"); Es=ensure(Es,"shaft.E"); ri=ensure(ri,"hub.r_i"); ro=ensure(ro,"hub.r_o"); Eh=ensure(Eh,"hub.E"); delta=ensure(delta,"fit.delta")
    Cs=(1/Es)*((1 - nus**2)/rs); Ch=(1/Eh)*(((1 - nuh**2)*(ro**2 + ri**2))/((ro**2 - ri**2)*ri))
    p = delta/(Cs + Ch); return {"contact_pressure": p}
