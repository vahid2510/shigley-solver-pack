
import math
from .common import to_si, ensure
def flat_belt_power(inputs):
    T1=to_si(inputs.get("loads",{}).get("T1")); T2=to_si(inputs.get("loads",{}).get("T2")); v=to_si(inputs.get("operating",{}).get("v"))
    T1=ensure(T1,"loads.T1"); T2=ensure(T2,"loads.T2"); v=ensure(v,"operating.v")
    return {"P": (T1 - T2)*v}
def tension_ratio(inputs):
    mu=to_si(inputs.get("tribology",{}).get("mu")); theta=to_si(inputs.get("geometry",{}).get("theta"))
    mu=ensure(mu,"tribology.mu"); theta=ensure(theta,"geometry.theta")
    return {"T1_over_T2": math.e**(mu*theta)}
