# builder_core.py — self-contained ProblemSpec builder (Phase-1)
import re, json, math
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

UNIT2SI = {
  "m": ("Length", 1.0), "meter": ("Length", 1.0), "meters": ("Length", 1.0),
  "mm": ("Length", 1e-3), "cm": ("Length", 1e-2), "in": ("Length", 0.0254), "ft": ("Length", 0.3048),
  "m^2": ("Area", 1.0), "mm^2": ("Area", 1e-6), "in^2": ("Area", 0.00064516),
  "m^4": ("Inertia", 1.0), "mm^4": ("Inertia", 1e-12), "in^4": ("Inertia", 4.162314e-7),
  "n": ("Force", 1.0), "kn": ("Force", 1e3), "lbf": ("Force", 4.4482216152605),
  "n/m": ("Force/Length", 1.0), "kn/m": ("Force/Length", 1e3), "lbf/ft": ("Force/Length", 4.4482216152605/0.3048),
  "pa": ("Pressure", 1.0), "kpa": ("Pressure", 1e3), "mpa": ("Pressure", 1e6), "gpa": ("Pressure", 1e9), "psi": ("Pressure", 6894.757293168),
  "kg": ("Mass", 1.0), "lbm": ("Mass", 0.45359237),
  "n*s/m": ("ViscDamp", 1.0),
  "n/mm": ("Force/Length", 1e3),
  "m/s^2": ("Accel", 1.0), "g": ("Accel", 9.81),
  "m/s": ("Velocity", 1.0), "cm/s": ("Velocity", 0.01), "mm/s": ("Velocity", 0.001), "ft/s": ("Velocity", 0.3048),
  "hz": ("Freq", 1.0),
  "n*m": ("Torque", 1.0), "kn*m": ("Torque", 1e3),
  "rpm": ("Freq", 1.0),
  "rev": ("Count", 1.0),
  "hour": ("Time", 1.0), "hours": ("Time", 1.0), "hr": ("Time", 1.0), "hrs": ("Time", 1.0),
  "k": ("Temp", 1.0), "c": ("Temp", 1.0)
}
NUM = r"(?:\d+(?:\.\d+)?(?:e[+\-]?\d+)?)"; UN_BY = r"(?:by|x|x)"; SP = r"[ \t]+"

SUPERSCRIPT_MAP = str.maketrans({
  "\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3",
  "\u2074": "4", "\u2075": "5", "\u2076": "6", "\u2077": "7",
  "\u2078": "8", "\u2079": "9", "\u207b": "-", "\u207a": "+",
  "\u00b7": "*", "\u2219": "*", "\u00d7": "x"
})

def normalize_text(text: str) -> str:
  t = text.translate(SUPERSCRIPT_MAP)
  def repl(match):
    coeff = match.group(1)
    exp = match.group(2)
    return f"{coeff}e{exp}"
  t = re.sub(r"(\d+(?:\.\d+)?)\s*(?:[x\*])\s*10\s*(?:\^)?\s*([+\-]?\d+)", repl, t, flags=re.I)
  t = re.sub(r"\b(mm|cm|m|in)(\d+)", lambda m: f"{m.group(1)}^{m.group(2)}", t, flags=re.I)
  t = re.sub(r"(?<=\d)\s+(?=\d)", "", t)
  return t

def norm_unit(u: str) -> str:
  u = (u or "").strip().lower()
  for token in ("·", "∙", "×"):
    u = u.replace(token, "*")
  u = u.replace(" ", "")
  return u

@dataclass
class Quantity:
  value: float; unit: str; dim: str; si: float

def make_qty(val: float, ustr: str)->Optional[Quantity]:
  u = norm_unit(ustr)
  if u in UNIT2SI:
    dim, k = UNIT2SI[u]
    return Quantity(val, ustr, dim, val*k)
  return None

def contains_any(text:str, words:List[str])->bool:
  return any(re.search(rf"\b{re.escape(w)}\b", text, re.I) for w in words)

def add_output(outputs: List[Dict[str,Any]], metric:str, unit_pref:str=None, at:str=None, desc:str=None):
  item={"metric":metric}; 
  if unit_pref: item["unit_pref"]=unit_pref
  if at: item["at"]=at
  if desc: item["description"]=desc
  outputs.append(item)

def safe_float(s): 
  try: return float(s)
  except: return None


def parse_value_unit(text:str, key_pattern:str, units:List[str])->Optional[Quantity]:
  units_sorted = sorted(units, key=len, reverse=True)
  ualt = "|".join(map(re.escape, units_sorted))
  pat = rf"(?:{key_pattern})(?:[^0-9]*?)({NUM})\s*({ualt})"
  m = re.search(pat, text, re.I)
  if not m: return None
  val = safe_float(m.group(1)); unit = m.group(2) if len(m.groups())>=2 else None
  if val is None or unit is None: return None
  return make_qty(val, unit)

def parse_single_num_unit(text:str, key_pattern:str, units:List[str])->Optional[Quantity]:
  units_sorted = sorted(units, key=len, reverse=True)
  ualt = "|".join(map(re.escape, units_sorted))
  pat1 = rf"(?:{key_pattern})(?:[^0-9]*?)({NUM})\s*({ualt})"
  m = re.search(pat1, text, re.I)
  if not m:
    pat2 = rf"({NUM})\s*({ualt}).{{0,40}}(?:{key_pattern})"
    m = re.search(pat2, text, re.I)
  if not m: return None
  val = safe_float(m.group(1)); unit = m.group(2)
  if val is None: return None
  return make_qty(val, unit)
def parse_rect_section(text:str):
  pat = rf"({NUM})\s*(mm|cm|m|in){SP}?(?:{UN_BY}){SP}?({NUM})\s*(mm|cm|m|in)"
  m = re.search(pat, text, re.I)
  if not m: return None
  b = make_qty(safe_float(m.group(1)), m.group(2))
  h = make_qty(safe_float(m.group(3)), m.group(4))
  if not b or not h: return None
  return (b,h)


def parse_eq_assign(text:str, symbol_pattern:str, units:List[str])->Optional[Quantity]:
  units_sorted = sorted(units, key=len, reverse=True)
  ualt = "|".join(map(re.escape, units_sorted))
  pat = rf"(?:{symbol_pattern})\s*=\s*({NUM})\s*({ualt})"
  m = re.search(pat, text, re.I)
  if not m: return None
  val = safe_float(m.group(1)); unit = m.group(2)
  if val is None: return None
  return make_qty(val, unit)
def classify(text:str):
  cand=[]
  s=0.0
  if contains_any(text, ["simply supported","pinned and roller","pinned-roller"]): s+=0.4
  if re.search(r"\b(uniformly distributed load|distributed load|udl)\b", text, re.I): s+=0.4
  if re.search(r"\bbeam|span|midspan\b", text, re.I): s+=0.2
  cand.append(("beam.eb.simply_supported.udl", s))

  s=0.0
  if re.search(r"\bthin[\- ]walled\b", text, re.I): s+=0.4
  if re.search(r"\b(cylindrical vessel|cylinder|pressure vessel)\b", text, re.I): s+=0.4
  if re.search(r"\binternal pressure|hoop|longitudinal\b", text, re.I): s+=0.2
  cand.append(("pv.cylinder.thin", s))

  s=0.0
  if re.search(r"\bbuckling|critical load|euler\b", text, re.I): s+=0.6
  if re.search(r"\bcolumn|end condition|effective length factor|K\s*=\b", text, re.I): s+=0.3
  cand.append(("column.euler.buckling", s))

  s=0.0
  if re.search(r"\bshaft\b", text, re.I): s+=0.3
  if re.search(r"\bbearing\b", text, re.I): s+=0.2
  if re.search(r"\bgear|pulley|torque\b", text, re.I): s+=0.3
  if re.search(r"\bsegment|step|diameter\b", text, re.I): s+=0.2
  cand.append(("shaft.analysis.segmented", s))

  s=0.0
  if re.search(r"\bbearing\b", text, re.I): s+=0.4
  if re.search(r"\bequivalent dynamic load|P[_\s]?=\b", text, re.I): s+=0.4
  if re.search(r"\bthrust|axial\b", text, re.I): s+=0.2
  cand.append(("bearing.ball.equivalent_load", s))

  s=0.0
  if re.search(r"\bbearing\b", text, re.I): s+=0.3
  if re.search(r"\brequired dynamic rating|minimum rating|C_required\b", text, re.I): s+=0.5
  if re.search(r"\blife|hours|reliability\b", text, re.I): s+=0.2
  cand.append(("bearing.ball.required_C", s))

  s=0.0
  if re.search(r"\bbearing\b", text, re.I): s+=0.3
  if re.search(r"\bL10\b|\blife\b", text, re.I): s+=0.4
  if re.search(r"\breliability\b|a1\b", text, re.I): s+=0.2
  cand.append(("bearing.ball.life_reliability", s))

  s=0.0
  if re.search(r"\bpower\s+screw\b", text, re.I): s+=0.6
  if re.search(r"\bsquare[-\s]*thread\b|\blead\b|\bpitch\b", text, re.I): s+=0.2
  if re.search(r"\bself[-\s]*locking\b|\bturns\b|\bstarts\b", text, re.I): s+=0.1
  cand.append(("power.screw.raise", s))

  s=0.0
  if re.search(r"\bdisc?\s*brake\b|\bsingle[-\s]*disc\s*clutch\b", text, re.I): s+=0.5
  if re.search(r"\buniform\s+wear\b", text, re.I): s+=0.3
  if re.search(r"\bfriction\b|\bnormal force\b|\bbraking force\b", text, re.I): s+=0.2
  cand.append(("clutch.single_disc.uniform_wear", s))

  s=0.0
  if re.search(r"\bdisc?\s*brake\b|\bsingle[-\s]*disc\s*clutch\b", text, re.I): s+=0.5
  if re.search(r"\buniform\s+pressure\b", text, re.I): s+=0.3
  if re.search(r"\bfriction\b|\bnormal force\b|\bbraking force\b", text, re.I): s+=0.2
  cand.append(("clutch.single_disc.uniform_pressure", s))

  s=0.0
  if re.search(r"\bflat\s+belt\b|\bbelt drive\b|\bbelt\b", text, re.I): s+=0.4
  if re.search(r"\btight[-\s]?side\b|\bT1\b", text, re.I): s+=0.3
  if re.search(r"\bslack[-\s]?side\b|\bT2\b", text, re.I): s+=0.2
  if re.search(r"\bspeed\b|\bvelocity\b|\blinear speed\b", text, re.I): s+=0.1
  cand.append(("belt.flat.power", s))

  s=0.0
  if re.search(r"\bflat\s+belt\b|\bbelt drive\b|\bbelt\b", text, re.I): s+=0.4
  if re.search(r"\bfriction\b|\bmu\b|μ", text, re.I): s+=0.3
  if re.search(r"\bwrap\b|\bangle of contact\b|\btheta\b|θ", text, re.I): s+=0.3
  cand.append(("belt.flat.tension_ratio", s))

  s=0.0
  if re.search(r"\bextension spring\b", text, re.I): s+=0.5
  if re.search(r"\binitial tension|preload\b", text, re.I): s+=0.3
  if re.search(r"\bspring\b", text, re.I): s+=0.2
  cand.append(("spring.helical.extension", s))

  s=0.0
  if re.search(r"\btorsion spring\b", text, re.I): s+=0.5
  if re.search(r"\btorque|moment\b", text, re.I): s+=0.3
  if re.search(r"\bangle of twist|deflection angle\b", text, re.I): s+=0.2
  cand.append(("spring.helical.torsion", s))

  s=0.0
  if re.search(r"\bconcentric springs|compound spring|nested springs\b", text, re.I): s+=0.6
  if re.search(r"\bspring\b", text, re.I): s+=0.2
  if re.search(r"\btotal load|combined load\b", text, re.I): s+=0.2
  cand.append(("spring.helical.parallel", s))

  s=0.0
  if re.search(r"\bspring\b", text, re.I): s+=0.4
  if re.search(r"\bhelical|compression\b", text, re.I): s+=0.3
  if re.search(r"\b(active coils|Wahl)\b", text, re.I): s+=0.2
  cand.append(("spring.helical.compression", s))

  s=0.0
  if re.search(r"\bshaft\b", text, re.I): s+=0.4
  if re.search(r"\btorsion|torque\b", text, re.I): s+=0.4
  if re.search(r"\bangle of twist|twist\b", text, re.I): s+=0.2
  cand.append(("shaft.torsion.solid", s))

  s=0.0
  if re.search(r"\bsdof\b", text, re.I): s+=0.4
  if re.search(r"\bbase[\- ]excited|base acceleration\b", text, re.I): s+=0.4
  if re.search(r"\bharmonic|hz|frequency\b", text, re.I): s+=0.2
  cand.append(("dyn.sdof.base_excited.harmonic", s))

  best = max(cand, key=lambda x:x[1])
  return best[0], min(1.0, max(0.0, best[1]))

def extract_beam_udl(text:str):
  inputs={"geometry":{}, "material":{}, "loads":[], "supports":[]}
  L = parse_single_num_unit(text, r"(?:span|length|L)", ["m","mm","cm","in","ft"])
  if L: inputs["geometry"]["L"] = L.__dict__
  sec = parse_rect_section(text)
  if sec:
    b,h=sec
    inputs["geometry"]["section"]={"shape":"rect","b":b.__dict__,"h":h.__dict__}
  E = parse_eq_assign(text, r"(?:E|Young(?:'s)? modulus|modulus)", ["Pa","MPa","GPa","psi"])
  if E: inputs["material"]["E"]=E.__dict__
  mnu = re.search(r"(?:ν|nu|poisson(?:'s)?\s*ratio)[^\n\r]*?"+NUM, text, re.I)
  if mnu:
    m2 = re.search(NUM, mnu.group(0), re.I)
    if m2:
      try:
        val = float(m2.group(0))
        inputs["material"]["nu"]={"value":val,"unit":"-","dim":"None","si":val}
      except: pass
  q = parse_value_unit(text, r"(?:uniformly distributed load|distributed load|udl|q|w0)", ["N/m","kN/m","lbf/ft"])
  if q:
    inputs["loads"].append({"type":"uniform","q":q.__dict__,"region":"span","direction":"-y"})
  if re.search(r"\bsimply supported|pinned and roller|pinned-roller\b", text, re.I):
    inputs["supports"]=[{"type":"pinned","at":"x=0"},{"type":"roller","at":"x=L"}]
  outputs=[]
  if re.search(r"\bdeflection\b", text, re.I): add_output(outputs,"deflection_mid","mm")
  if re.search(r"\bbending stress|von mises|maximum stress\b", text, re.I): add_output(outputs,"sigma_bending_max","MPa")
  if re.search(r"\breaction", text, re.I): add_output(outputs,"reactions")
  if not outputs:
    add_output(outputs,"deflection_mid","mm"); add_output(outputs,"sigma_bending_max","MPa")
  return inputs, outputs

def extract_pv_cylinder(text:str):
  inputs={"geometry":{}, "material":{}, "loads":[], "supports":[]}
  R = parse_value_unit(text, r"(?:radius|R)", ["m","mm","in"])
  t = parse_value_unit(text, r"(?:wall thickness|thickness|t\b)", ["m","mm","in"])
  if R: inputs["geometry"]["R"]=R.__dict__
  if t: inputs["geometry"]["t"]=t.__dict__
  p = parse_value_unit(text, r"(?:internal pressure|pressure|p)", ["Pa","kPa","MPa","psi"])
  if p: inputs["loads"].append({"type":"pressure","p":p.__dict__})
  sy = parse_eq_assign(text, r"(?:σ_y|sigma_y|yield strength|sy)", ["Pa","MPa","psi"])
  if sy: inputs["material"]["sigma_y"]=sy.__dict__
  outputs=[]
  add_output(outputs,"sigma_hoop","MPa"); add_output(outputs,"sigma_longitudinal","MPa")
  if re.search(r"\bfactor of safety|fos|safety factor\b", text, re.I): add_output(outputs,"fos_yield")
  return inputs, outputs

def extract_column_buckling(text:str):
  inputs={"geometry":{}, "material":{}, "loads":[], "supports":[]}
  E = parse_value_unit(text, r"(?:E|modulus)", ["Pa","MPa","GPa","psi"])
  if E: inputs["material"]["E"]=E.__dict__
  I = parse_value_unit(text, r"(?:I|second moment)", ["mm^4","m^4","in^4"])
  if I: inputs["geometry"]["I"]=I.__dict__
  L = parse_value_unit(text, r"(?:length|L)", ["mm","m","in","ft"])
  if L: inputs["geometry"]["L"]=L.__dict__
  K=None
  if re.search(r"\bpinned-pinned|pinned at both ends|both ends pinned\b", text, re.I): K=1.0
  elif re.search(r"\bfixed-free|cantilever\b", text, re.I): K=2.0
  elif re.search(r"\bfixed-fixed\b", text, re.I): K=0.5
  elif re.search(r"\bfixed-pinned\b", text, re.I): K=0.7
  if K is not None: inputs["geometry"]["K"]={"value":K,"unit":"-","dim":"None","si":K}
  else:
    mK = re.search(rf"K\s*=\s*({NUM})", text, re.I)
    if mK:
      val = safe_float(mK.group(1))
      if val is not None:
        inputs["geometry"]["K"]={"value":val,"unit":"-","dim":"None","si":val}
  outputs=[{"metric":"P_cr","unit_pref":"N"}]
  return inputs, outputs

def extract_sdof_base(text:str):
  inputs={"system":{}, "excitation":{}}
  m = parse_value_unit(text, r"(?:m|mass)", ["kg","lbm"])
  if m: inputs["system"]["m"]=m.__dict__
  k = parse_value_unit(text, r"(?:k|stiffness)", ["N/m","lbf/ft"])
  if k: inputs["system"]["k"]=k.__dict__
  mnu = re.search(r"(?:ζ|zeta|damping ratio)[^\n\r]*?"+NUM, text, re.I)
  if mnu:
    m2 = re.search(NUM, mnu.group(0), re.I)
    if m2:
        try:
            val = float(m2.group(0))
            inputs["system"]["zeta"]={"value":val,"unit":"-","dim":"None","si":val}
        except: pass
  a0 = parse_value_unit(text, r"(?:base acceleration|acceleration)", ["m/s^2","g"])
  f = parse_value_unit(text, r"(?:frequency|f)", ["Hz"])
  if a0: inputs["excitation"]["a0"]=a0.__dict__
  if f: inputs["excitation"]["f"]=f.__dict__
  outputs=[{"metric":"x_peak","unit_pref":"mm"}]
  return inputs, outputs

def make_unitless(val: Optional[float]) -> Optional[Dict[str, Any]]:
  if val is None:
    return None
  return {"value": val, "unit": "-", "dim": "None", "si": val}

def parse_reliability_value(text:str)->Optional[float]:
  m = re.search(rf"({NUM})\s*%\s*(?:reliability)", text, re.I)
  if not m:
    m = re.search(rf"(?:reliability)\s*(?:=|of)?\s*({NUM})\s*%", text, re.I)
  if not m:
    m = re.search(rf"\bR\s*=\s*({NUM})\s*%", text, re.I)
  if not m:
    m = re.search(rf"(?:reliability)\s*(?:=|of)?\s*({NUM})", text, re.I)
  if not m:
    m = re.search(rf"\bR\s*=\s*({NUM})", text, re.I)
  if not m:
    return None
  val = safe_float(m.group(1))
  if val is None:
    return None
  if val > 1.0:
    val = val / 100.0
  return val

def extract_bearing_life(text:str):
  inputs={"catalog":{}, "loads":{}, "operating":{}, "reliability":{}, "bearing":{}}
  C = parse_value_unit(text, r"(?:dynamic rating|C10|C)\b", ["N","kN","lbf"])
  if C: inputs["catalog"]["C"]=C.__dict__
  P = parse_value_unit(text, r"(?:equivalent radial load|equivalent dynamic load|equivalent load|radial load)", ["N","kN","lbf"])
  if P: inputs["loads"]["P"]=P.__dict__
  rpm = parse_value_unit(text, r"(?:speed|rpm|n)", ["rpm"])
  if rpm: inputs["operating"]["rpm"]=rpm.__dict__
  elif (m := re.search(rf"({NUM})\s*rpm", text, re.I)):
    val = safe_float(m.group(1))
    q = make_qty(val, "rpm") if val is not None else None
    if q: inputs["operating"]["rpm"]=q.__dict__
  R = parse_reliability_value(text)
  if R is not None:
    inputs["reliability"]["R"]=make_unitless(R)
  p_match = re.search(r"\bp\s*=\s*({NUM})", text, re.I)
  if p_match:
    val = safe_float(p_match.group(1))
    if val is not None:
      inputs["bearing"]["p"]=make_unitless(val)
  outputs=[]
  add_output(outputs,"L10_hours","hours")
  add_output(outputs,"L10_rev","rev")
  return inputs, outputs

def extract_bearing_required_rating(text:str):
  inputs={"loads":{}, "operating":{}, "life":{}, "reliability":{}, "bearing":{}}
  P = parse_value_unit(text, r"(?:equivalent radial load|equivalent dynamic load|equivalent load|radial load)", ["N","kN","lbf"])
  if P: inputs["loads"]["P"]=P.__dict__
  rpm = parse_value_unit(text, r"(?:speed|rpm|n)", ["rpm"])
  if rpm: inputs["operating"]["rpm"]=rpm.__dict__
  elif (m_rpm := re.search(rf"({NUM})\s*rpm", text, re.I)):
    val = safe_float(m_rpm.group(1))
    q = make_qty(val, "rpm") if val is not None else None
    if q: inputs["operating"]["rpm"]=q.__dict__
  life_hours = parse_value_unit(text, r"(?:life|service life|Lna)", ["hour","hours","hr","hrs"])
  if life_hours: inputs.setdefault("life",{})["hours"]=life_hours.__dict__
  life_rev = parse_value_unit(text, r"(?:revolutions|rev)", ["rev"])
  if life_rev: inputs.setdefault("life",{})["rev"]=life_rev.__dict__
  if "hours" not in inputs.get("life", {}):
    m_hours = re.search(rf"({NUM})\s*(?:hours|hrs|hr)", text, re.I)
    if m_hours:
      val = safe_float(m_hours.group(1))
      q = make_qty(val, "hours") if val is not None else None
      if q: inputs.setdefault("life",{})["hours"]=q.__dict__
  R = parse_reliability_value(text)
  if R is not None:
    inputs["reliability"]["R"]=make_unitless(R)
  p_match = re.search(r"\bp\s*=\s*({NUM})", text, re.I)
  if p_match:
    val = safe_float(p_match.group(1))
    if val is not None:
      inputs["bearing"]["p"]=make_unitless(val)
  outputs=[]
  add_output(outputs,"C_required","N")
  return inputs, outputs

def extract_bearing_equivalent(text:str):
  inputs={"loads":{}, "factors":{}}
  Fr = parse_value_unit(text, r"(?:radial load|F_r)", ["N","kN","lbf"])
  if Fr: inputs["loads"]["F_r"]=Fr.__dict__
  Fa = parse_value_unit(text, r"(?:axial load|thrust load|F_a)", ["N","kN","lbf"])
  if Fa: inputs["loads"]["F_a"]=Fa.__dict__
  V_match = re.search(r"\bV\s*=\s*({NUM})", text, re.I)
  if V_match:
    val = safe_float(V_match.group(1))
    if val is not None:
      inputs["factors"]["V"]=make_unitless(val)
  for symbol in ("X","Y","e"):
    m = re.search(rf"\b{symbol}\s*=\s*({NUM})", text, re.I)
    if m:
      val = safe_float(m.group(1))
      if val is not None:
        key = symbol if symbol != "e" else "e"
        inputs["factors"][key]=make_unitless(val)
  outputs=[]
  add_output(outputs,"P_equivalent","N")
  add_output(outputs,"Fa_over_Fr")
  return inputs, outputs

def extract_spring_helical(text:str, mode:str="compression"):
  inputs={"geometry":{}, "material":{}, "loads":{}}
  d = parse_value_unit(text, r"(?:wire diameter|wire dia|d\b)", ["mm","cm","m","in"])
  if d: inputs["geometry"]["d"]=d.__dict__
  D = parse_value_unit(text, r"(?:mean coil diameter|mean diameter|D\b)", ["mm","cm","m","in"])
  if D: inputs["geometry"]["D"]=D.__dict__
  na_match = re.search(rf"(?:active coils|n_a|N_a)\s*(?:=)?\s*({NUM})", text, re.I)
  if na_match:
    val = safe_float(na_match.group(1))
    unitless = make_unitless(val)
    if unitless: inputs["geometry"]["n_a"]=unitless
  G = parse_value_unit(text, r"(?:shear modulus|G)", ["Pa","kPa","MPa","GPa","psi"])
  if G: inputs["material"]["G"]=G.__dict__
  F = parse_value_unit(text, r"(?:load|F)", ["N","kN"])
  if F: inputs["loads"]["F"]=F.__dict__
  if mode=="extension":
    Fi = parse_value_unit(text, r"(?:initial tension|F_i|preload)", ["N","kN"])
    if Fi: inputs["loads"]["F_initial"]=Fi.__dict__
  outputs=[]
  add_output(outputs,"k","N/m")
  add_output(outputs,"deflection","mm")
  add_output(outputs,"tau_max","MPa")
  add_output(outputs,"Wahl_factor")
  return inputs, outputs

def extract_torsion_solid(text:str):
  inputs={"geometry":{}, "material":{}, "loads":{}}
  L = parse_value_unit(text, r"(?:length|L)", ["mm","cm","m","in","ft"])
  if L: inputs["geometry"]["L"]=L.__dict__
  d = parse_value_unit(text, r"(?:diameter|dia)", ["mm","cm","m","in"])
  if d: inputs["geometry"]["d"]=d.__dict__
  G = parse_value_unit(text, r"(?:shear modulus|G)", ["Pa","kPa","MPa","GPa","psi"])
  if G: inputs["material"]["G"]=G.__dict__
  T = parse_value_unit(text, r"(?:torque|T)", ["N*m","kN*m"])
  if T: inputs["loads"]["T"]=T.__dict__
  outputs=[]
  add_output(outputs,"tau_max","MPa")
  add_output(outputs,"theta","deg")
  add_output(outputs,"J","m^4")
  return inputs, outputs

def extract_power_screw(text:str):
  inputs = {"geometry": {}, "tribology": {}, "loads": {}}
  outputs: List[Dict[str, Any]] = []
  warnings: List[str] = []

  F = parse_value_unit(text, r"(?:axial load|lifting load|load|force)", ["N", "kN", "lbf"])
  if F:
    inputs["loads"]["F"] = F.__dict__

  d_m = parse_value_unit(text, r"(?:mean diameter|mean thread diameter|d_m|dm)", ["mm", "cm", "m", "in"])
  if d_m:
    inputs["geometry"]["d_m"] = d_m.__dict__
  else:
    for match in re.finditer(rf"({NUM})\s*(mm|cm|m|in)", text, re.I):
      val = safe_float(match.group(1))
      qty = make_qty(val, match.group(2))
      if not qty:
        continue
      window = text[max(0, match.start() - 25):match.start()].lower()
      window_after = text[match.end():match.end() + 25].lower()
      if "mean diameter" in window or ("mean" in window and "diameter" in window_after):
        inputs["geometry"]["d_m"] = qty.__dict__
        break

  lead = parse_value_unit(text, r"(?:lead)", ["mm", "cm", "m", "in"])
  pitch = parse_value_unit(text, r"(?:pitch)", ["mm", "cm", "m", "in"])
  starts = None
  if re.search(r"\bdouble[-\s]?start\b", text, re.I):
    starts = 2
  elif re.search(r"\btriple[-\s]?start\b", text, re.I):
    starts = 3
  elif re.search(r"\bsingle[-\s]?start\b", text, re.I):
    starts = 1
  else:
    m_starts = re.search(rf"({NUM})\s*(?:start|starts)", text, re.I)
    if m_starts:
      starts = safe_float(m_starts.group(1))
  if starts:
    unitless = make_unitless(starts)
    if unitless:
      inputs["geometry"]["n_starts"] = unitless

  if lead:
    inputs["geometry"]["lead"] = lead.__dict__
  elif pitch:
    inputs["geometry"]["pitch"] = pitch.__dict__

  d_c = parse_value_unit(text, r"(?:collar diameter|mean collar diameter|d_c)", ["mm", "cm", "m", "in"])
  if d_c:
    inputs["geometry"]["d_collar"] = d_c.__dict__
  else:
    for match in re.finditer(rf"({NUM})\s*(mm|cm|m|in)", text, re.I):
      val = safe_float(match.group(1))
      qty = make_qty(val, match.group(2))
      if not qty:
        continue
      window = text[max(0, match.start() - 25):match.start()].lower()
      window_after = text[match.end():match.end() + 25].lower()
      if "collar" in window or "collar" in window_after:
        inputs["geometry"]["d_collar"] = qty.__dict__
        break

  def parse_mu(patterns: List[str]) -> Optional[Dict[str, Any]]:
    for pat in patterns:
      m = re.search(pat, text, re.I)
      if m:
        val = safe_float(m.group(1))
        unitless = make_unitless(val)
        if unitless:
          return unitless
    return None

  mu_qty = parse_mu([
    r"(?:coefficient of friction|friction coefficient|thread friction(?: coefficient)?)\s*(?:=|is|of)?\s*(" + NUM + r")",
    r"(?:μ|mu)\s*(?:=|is)?\s*(" + NUM + r")",
  ])
  if mu_qty:
    inputs["tribology"]["mu"] = mu_qty

  mu_c_qty = parse_mu([
    r"(?:collar friction(?: coefficient)?|collar μ|mu_c)\s*(?:=|is|of)?\s*(" + NUM + r")",
  ])
  if mu_c_qty:
    inputs["tribology"]["mu_collar"] = mu_c_qty

  add_output(outputs, "T_total_raise", "N*m")
  add_output(outputs, "T_thread_raise", "N*m")
  add_output(outputs, "T_collar", "N*m")
  add_output(outputs, "efficiency")
  add_output(outputs, "self_locking")
  add_output(outputs, "helix_angle", "rad")

  if "F" not in inputs["loads"]:
    warnings.append("Axial load not detected.")
  if "d_m" not in inputs["geometry"]:
    warnings.append("Mean thread diameter not detected.")
  if "lead" not in inputs["geometry"] and "pitch" not in inputs["geometry"]:
    warnings.append("Thread lead or pitch not detected.")

  return inputs, outputs, warnings

def extract_disc_brake_uniform_wear(text:str):
  return _extract_disc_brake_common(text)

def extract_disc_brake_uniform_pressure(text:str):
  return _extract_disc_brake_common(text)

def extract_belt_power(text:str):
  inputs = {"loads": {}, "operating": {}}
  outputs: List[Dict[str, Any]] = []
  warnings: List[str] = []

  def parse_force(pattern: str) -> Optional[Dict[str, Any]]:
    qty = parse_value_unit(text, pattern, ["N", "kN", "lbf"])
    if qty:
      return qty.__dict__
    return None

  T1 = parse_force(r"(?:tight[-\s]?side tension|tight tension|T1)")
  if T1:
    inputs["loads"]["T1"] = T1
  T2 = parse_force(r"(?:slack[-\s]?side tension|loose tension|T2)")
  if T2:
    inputs["loads"]["T2"] = T2

  v = parse_value_unit(text, r"(?:belt speed|linear speed|belt velocity|velocity)", ["m/s", "cm/s", "mm/s", "ft/s"])
  if v:
    inputs["operating"]["v"] = v.__dict__

  add_output(outputs, "P", "W")

  if "T1" not in inputs["loads"]:
    warnings.append("Tight-side tension T1 not detected.")
  if "T2" not in inputs["loads"]:
    warnings.append("Slack-side tension T2 not detected.")
  if "v" not in inputs["operating"]:
    warnings.append("Belt speed not detected.")

  return inputs, outputs, warnings

def extract_belt_tension_ratio(text:str):
  inputs = {"tribology": {}, "geometry": {}}
  outputs: List[Dict[str, Any]] = []
  warnings: List[str] = []

  def parse_mu():
    pattern1 = re.compile(rf"(?:friction coefficient|coefficient of friction)[^0-9]{{0,40}}({NUM})", re.I)
    m = pattern1.search(text)
    if m:
      val = safe_float(m.group(1))
      unitless = make_unitless(val)
      if unitless:
        return unitless
    pattern2 = re.compile(rf"(?:μ|mu)[^0-9]{{0,40}}({NUM})", re.I)
    m = pattern2.search(text)
    if m:
      val = safe_float(m.group(1))
      unitless = make_unitless(val)
      if unitless:
        return unitless
    return None

  def parse_theta():
    match = re.search(r"(" + NUM + r")\s*(deg|degree|degrees)", text, re.I)
    if match:
      val = safe_float(match.group(1))
      if val is not None:
        return {"value": val, "unit": "deg", "dim": "Angle", "si": math.radians(val)}
    match = re.search(r"(" + NUM + r")\s*(rad|radian|radians)", text, re.I)
    if match:
      val = safe_float(match.group(1))
      if val is not None:
        return {"value": val, "unit": "rad", "dim": "Angle", "si": val}
    match = re.search(r"(?:wrap angle|angle of contact|theta|θ)\s*(?:=|is)?\s*(" + NUM + r")", text, re.I)
    if match:
      val = safe_float(match.group(1))
      if val is not None:
        return {"value": val, "unit": "rad", "dim": "Angle", "si": val}
    return None

  mu_qty = parse_mu()
  if mu_qty:
    inputs["tribology"]["mu"] = mu_qty

  theta_qty = parse_theta()
  if theta_qty:
    inputs["geometry"]["theta"] = theta_qty

  add_output(outputs, "T1_over_T2")

  if "mu" not in inputs["tribology"]:
    warnings.append("Coefficient of friction not detected.")
  if "theta" not in inputs["geometry"]:
    warnings.append("Wrap/contact angle not detected.")

  return inputs, outputs, warnings

def _extract_disc_brake_common(text:str):
  inputs = {"geometry": {}, "tribology": {}, "loads": {}}
  outputs: List[Dict[str, Any]] = []
  warnings: List[str] = []

  F = parse_value_unit(text, r"(?:normal force|braking force|clamping force|load)", ["N", "kN", "lbf"])
  if F:
    inputs["loads"]["F"] = F.__dict__

  mu = parse_value_unit(text, r"(?:friction coefficient|coefficient of friction|μ|mu)", ["-", ""])
  if mu:
    inputs["tribology"]["mu"] = mu.__dict__

  r_i = parse_value_unit(text, r"(?:inner radius|inside radius|r_i)", ["mm", "cm", "m", "in"])
  if r_i:
    inputs["geometry"]["r_i"] = r_i.__dict__
  r_o = parse_value_unit(text, r"(?:outer radius|outside radius|r_o)", ["mm", "cm", "m", "in"])
  if r_o:
    inputs["geometry"]["r_o"] = r_o.__dict__

  add_output(outputs, "T", "N*m")

  if "F" not in inputs["loads"]:
    warnings.append("Normal/braking force not detected.")
  if "r_i" not in inputs["geometry"]:
    warnings.append("Inner radius not detected.")
  if "r_o" not in inputs["geometry"]:
    warnings.append("Outer radius not detected.")

  return inputs, outputs, warnings

def extract_shaft_segmented(text: str):
  inputs = {"segments": [], "supports": [], "loads": [], "material": {}}
  outputs = [
    {"metric": "max_von_mises", "unit_pref": "MPa"},
    {"metric": "reactions"},
    {"metric": "max_moment", "unit_pref": "N*m"},
    {"metric": "twist_total", "unit_pref": "rad"}
  ]

  warnings: List[str] = []
  unresolved_notes: List[str] = []

  def unit_to_m(val, unit):
    if val is None or unit is None:
      return None
    u = unit.lower()
    if u in ("mm", "millimeter", "millimetre"):
      return val / 1000.0
    if u in ("cm", "centimeter", "centimetre"):
      return val / 100.0
    if u in ("m", "meter", "metre"):
      return val
    if u in ("in", "inch", "inches"):
      return val * 0.0254
    if u in ("ft", "foot", "feet"):
      return val * 0.3048
    return None

  def unit_to_force(val, unit):
    if val is None or unit is None:
      return None
    u = unit.lower().replace(" ", "")
    if u in ("kn", "kilonewton", "kilonewtons"):
      return val * 1000.0
    if u in ("n", "newton", "newtons"):
      return val
    if u in ("lb", "lbs", "lbf", "pound", "pounds", "poundforce"):
      return val * 4.4482216152605
    return None

  def unit_to_line_force(val, unit):
    if val is None or unit is None:
      return None
    u = unit.lower().replace(" ", "")
    u = u.replace("·", "*").replace("⋅", "*").replace("per", "/")
    if u in ("n/m", "newton/m", "newtons/m"):
      return val
    if u in ("kn/m", "kilonewton/m", "kilonewtons/m"):
      return val * 1000.0
    if u in ("n/mm", "newton/mm", "newtons/mm"):
      return val * 1000.0
    if u in ("kn/mm", "kilonewton/mm", "kilonewtons/mm"):
      return val * 1_000_000.0
    if u in ("n/cm", "newton/cm", "newtons/cm"):
      return val * 100.0
    if u in ("kn/cm", "kilonewton/cm", "kilonewtons/cm"):
      return val * 100_000.0
    if u in ("lbf/ft", "lb/ft", "pound/ft", "pounds/ft"):
      return val * (4.4482216152605 / 0.3048)
    if u in ("lbf/in", "lb/in", "pound/in", "pounds/in"):
      return val * (4.4482216152605 / 0.0254)
    return None

  def unit_to_torque(val, unit):
    if val is None or unit is None:
      return None
    u = unit.lower().replace("·", "*").replace("⋅", "*").replace(" ", "")
    if u in ("n*m", "nm"):
      return val
    if u in ("kn*m", "knm"):
      return val * 1000.0
    if u in ("lbf*ft", "lb*ft", "ft*lbf", "ft*lb"):
      return val * 1.3558179483314004
    if u in ("lbf*in", "lb*in", "in*lbf", "in*lb"):
      return val * 0.1129848290276167
    return None

  def detect_label_pair(snippet: str):
    if not snippet:
      return None
    snippet = snippet.replace("–", "-")
    patterns = [
      r"(?:segment|section|span)\s+([A-Z])(?:\s*[-/]\s*|(?:\s*to\s+))?([A-Z])",
      r"(?:between|from)\s+([A-Z])\s*(?:and|to)\s*([A-Z])",
      r"([A-Z])\s*-\s*([A-Z])",
      r"\b([A-Z])([A-Z])\s*(?:segment|span|portion)\b"
    ]
    excluded = {"ID", "OD"}
    for pat in patterns:
      m = re.search(pat, snippet, re.I)
      if m:
        a = m.group(1).upper()
        b = (m.group(2) or "").upper()
        if a and b and a.isalpha() and b.isalpha() and a != b:
          token = a + b
          if token not in excluded:
            return (a, b)
    m = re.search(r"\b([A-Z]{2})\b", snippet)
    if m:
      token = m.group(1).upper()
      if token not in excluded and token.isalpha():
        return (token[0], token[1])
    return None

  def spans_overlap(span_a, span_b):
    return not (span_a[1] <= span_b[0] or span_b[1] <= span_a[0])

  segment_meta: List[Dict[str, Any]] = []
  segment_spans: List[Tuple[int, int]] = []

  def add_segment_entry(d_o, length, d_i, label_pair, span):
    if d_o is None or length is None:
      return
    inputs["segments"].append({
      "d_o": d_o,
      "d_i": d_i if d_i else 0.0,
      "length": length
    })
    start_label = end_label = None
    if isinstance(label_pair, tuple):
      start_label, end_label = label_pair
    segment_meta.append({
      "label_start": start_label,
      "label_end": end_label,
      "length": length,
      "span": span
    })
    segment_spans.append(span)

  diam_pattern = re.compile(r"(?P<diam>" + NUM + r")\s*(?P<unit>mm|cm|m|in)\s*(?:diameter|dia)", re.I)
  length_patterns = [
    re.compile(r"(?P<len>" + NUM + r")\s*(?P<unit>mm|cm|m|in)\s*(?:long|length|span)", re.I),
    re.compile(r"(?:length|span)\s*(?:of\s*)?(?P<len>" + NUM + r")\s*(?P<unit>mm|cm|m|in)", re.I),
    re.compile(r"(?P<len>" + NUM + r")\s*(?P<unit>mm|cm|m|in)\s*(?:for\s+the\s+(?:first|next))", re.I)
  ]

  used_length_spans: List[Tuple[int, int]] = []

  for d_match in diam_pattern.finditer(text):
    window_start = max(0, d_match.start() - 160)
    window_end = min(len(text), d_match.end() + 200)
    best_length = None
    best_distance = None
    best_span = None
    best_match = None

    for pat in length_patterns:
      for l_match in pat.finditer(text, window_start, window_end):
        l_span = (l_match.start(), l_match.end())
        if any(spans_overlap(l_span, span) for span in used_length_spans):
          continue
        distance = abs((d_match.start() + d_match.end()) * 0.5 - (l_span[0] + l_span[1]) * 0.5)
        if best_distance is None or distance < best_distance:
          best_distance = distance
          best_span = l_span
          best_match = l_match
    if not best_match or best_span is None:
      continue

    d_val = safe_float(d_match.group("diam"))
    d_unit = d_match.group("unit")
    l_val = safe_float(best_match.group("len"))
    l_unit = best_match.group("unit")
    d_si = unit_to_m(d_val, d_unit)
    l_si = unit_to_m(l_val, l_unit)
    if d_si is None or l_si is None:
      continue

    span = (min(d_match.start(), best_span[0]), max(d_match.end(), best_span[1]))
    if any(spans_overlap(span, existing) for existing in segment_spans):
      continue

    context_before = text[max(0, d_match.start() - 60):d_match.start()]
    context_between = text[min(d_match.end(), best_span[0]):max(d_match.start(), best_span[1])]
    context_after = text[best_span[1]:min(len(text), best_span[1] + 60)]
    label = (
      detect_label_pair(context_before) or
      detect_label_pair(context_between) or
      detect_label_pair(context_after)
    )

    inner_window_start = max(0, span[0] - 20)
    inner_window_end = min(len(text), span[1] + 80)
    inner_window = text[inner_window_start:inner_window_end]
    inner_match = re.search(
      r"(?:inner(?:\s+|-)diameter|ID|bore|d_i)\s*(?:=|:|of)?\s*(" + NUM + r")\s*(mm|cm|m|in)",
      inner_window,
      re.I
    )
    d_i = None
    if inner_match:
      d_i = unit_to_m(safe_float(inner_match.group(1)), inner_match.group(2))

    add_segment_entry(d_si, l_si, d_i, label, span)
    used_length_spans.append(best_span)

  pair_order: List[Tuple[str, str]] = []
  length_by_pair: Dict[Tuple[str, str], float] = {}
  outer_by_pair: Dict[Tuple[str, str], float] = {}
  inner_by_pair: Dict[Tuple[str, str], float] = {}
  span_by_pair: Dict[Tuple[str, str], Tuple[int, int]] = {}

  def record_pair(dest: Dict[Tuple[str, str], float], pair: Tuple[str, str], value, span):
    if value is None:
      return
    if pair not in dest:
      dest[pair] = value
      span_by_pair.setdefault(pair, span)
      if pair not in pair_order:
        pair_order.append(pair)

  for pat, dest in [
    (re.compile(r"\bL[_\-]?([A-Z])([A-Z])\s*=\s*(" + NUM + r")\s*(mm|cm|m|in)\b", re.I), length_by_pair),
    (re.compile(r"\bD[_\-]?([A-Z])([A-Z])\s*=\s*(" + NUM + r")\s*(mm|cm|m|in)\b", re.I), outer_by_pair),
    (re.compile(r"\b(?:d_i|ID)[_\-]?([A-Z])([A-Z])\s*=\s*(" + NUM + r")\s*(mm|cm|m|in)\b", re.I), inner_by_pair),
  ]:
    for match in pat.finditer(text):
      pair = (match.group(1).upper(), match.group(2).upper())
      value = unit_to_m(safe_float(match.group(3)), match.group(4))
      record_pair(dest, pair, value, match.span())

  generic_pattern = re.compile(
    r"\b([A-Z])([A-Z])\b\s*(?:=|:)\s*(" + NUM + r")\s*(mm|cm|m|in)\b",
    re.I
  )
  diameter_keywords = ("diameter", "dia", "d_o", "outside")
  inner_keywords = ("inner", "inside", "bore", "d_i", "id")
  length_keywords = ("length", "long", "span", "between", "distance", "centre", "center", "c/c")

  for match in generic_pattern.finditer(text):
    pair = (match.group(1).upper(), match.group(2).upper())
    if pair[0] == pair[1]:
      continue
    value = unit_to_m(safe_float(match.group(3)), match.group(4))
    span = match.span()
    context = text[max(0, span[0] - 30):min(len(text), span[1] + 30)].lower()
    if any(kw in context for kw in inner_keywords):
      record_pair(inner_by_pair, pair, value, span)
    elif any(kw in context for kw in diameter_keywords):
      record_pair(outer_by_pair, pair, value, span)
    elif any(kw in context for kw in length_keywords):
      record_pair(length_by_pair, pair, value, span)

  existing_pairs = {
    (meta.get("label_start"), meta.get("label_end"))
    for meta in segment_meta
    if meta.get("label_start") and meta.get("label_end")
  }

  for pair in pair_order:
    if pair in existing_pairs:
      continue
    length_val = length_by_pair.get(pair)
    d_o_val = outer_by_pair.get(pair)
    if length_val is None or d_o_val is None:
      continue
    d_i_val = inner_by_pair.get(pair, 0.0) or 0.0
    add_segment_entry(d_o_val, length_val, d_i_val, pair, span_by_pair.get(pair, (0, 0)))
    existing_pairs.add(pair)

  if not inputs["segments"]:
    d = parse_value_unit(text, r"(?:shaft diameter|diameter)", ["mm", "cm", "m", "in"])
    L = parse_value_unit(text, r"(?:length|span|overall length|total length)", ["mm", "cm", "m", "in", "ft"])
    if not L:
      m_long = re.search(r"(" + NUM + r")\s*(mm|cm|m|in|ft)\s+long", text, re.I)
      if m_long:
        L = make_qty(safe_float(m_long.group(1)), m_long.group(2))
    if d and L:
      di = parse_value_unit(text, r"(?:inner diameter|bore|d_i)", ["mm", "cm", "m", "in"])
      add_segment_entry(d.si, L.si, di.si if di else 0.0, None, (0, 0))

  total_length = sum(seg["length"] for seg in inputs["segments"])
  node_positions: Dict[str, float] = {}

  # initial sequential positioning
  x_cursor = 0.0
  for idx, seg in enumerate(inputs["segments"]):
    meta = segment_meta[idx]
    start_label = meta.get("label_start")
    end_label = meta.get("label_end")
    if start_label and start_label not in node_positions:
      node_positions[start_label] = x_cursor
    if end_label and end_label not in node_positions:
      node_positions[end_label] = x_cursor + seg["length"]
    meta["x_start"] = node_positions.get(start_label, x_cursor)
    meta["x_end"] = node_positions.get(end_label, meta["x_start"] + seg["length"])
    x_cursor = meta["x_end"]

  # propagate positions using known lengths
  changed = True
  while changed:
    changed = False
    for idx, seg in enumerate(inputs["segments"]):
      meta = segment_meta[idx]
      start_label = meta.get("label_start")
      end_label = meta.get("label_end")
      length_val = seg["length"]
      if start_label and start_label in node_positions and end_label and end_label not in node_positions:
        node_positions[end_label] = node_positions[start_label] + length_val
        changed = True
      elif end_label and end_label in node_positions and start_label and start_label not in node_positions:
        node_positions[start_label] = node_positions[end_label] - length_val
        changed = True

  if node_positions:
    min_pos = min(node_positions.values())
    if abs(min_pos) > 1e-9:
      for key in list(node_positions.keys()):
        node_positions[key] -= min_pos

  x_cursor = 0.0
  for idx, seg in enumerate(inputs["segments"]):
    meta = segment_meta[idx]
    start_label = meta.get("label_start")
    end_label = meta.get("label_end")
    start_pos = node_positions.get(start_label)
    end_pos = node_positions.get(end_label)
    if start_pos is None:
      start_pos = x_cursor
    if end_pos is None:
      end_pos = start_pos + seg["length"]
    if start_label and start_label not in node_positions:
      node_positions[start_label] = start_pos
    if end_label and end_label not in node_positions:
      node_positions[end_label] = end_pos
    if abs((end_pos - start_pos) - seg["length"]) > 1e-6:
      end_pos = start_pos + seg["length"]
    meta["x_start"] = start_pos
    meta["x_end"] = end_pos
    x_cursor = end_pos

  if inputs["segments"]:
    total_length = max(meta["x_end"] for meta in segment_meta)

  def resolve_letter(letter: Optional[str]):
    if not letter:
      return None
    return node_positions.get(letter.upper())

  def resolve_distance(dist_val, ref_letter, context_text):
    if dist_val is None:
      return None
    base = 0.0
    if ref_letter:
      base = resolve_letter(ref_letter)
      if base is None:
        base = 0.0
    ctx = (context_text or "").lower()
    if ("from the right" in ctx or "from right" in ctx) and total_length:
      return max(0.0, total_length - dist_val)
    return base + dist_val

  def add_support(pos, label):
    if pos is None:
      return
    for existing in inputs["supports"]:
      if abs(existing["x"] - pos) < 1e-6:
        return
    inputs["supports"].append({"x": pos, "label": label})

  support_letter_hits: List[str] = []
  for match in re.finditer(r"(?:bearing|journal|support(?:ed)?|mounted)[^\.]{0,160}", text, re.I):
    snippet = match.group(0)
    for letter in re.findall(r"\b([A-Z])\b", snippet):
      letter = letter.upper()
      if letter in node_positions and letter not in support_letter_hits:
        support_letter_hits.append(letter)
    for num_match in re.finditer(r"(" + NUM + r")\s*(mm|cm|m|in|ft)", snippet, re.I):
      distance = unit_to_m(safe_float(num_match.group(1)), num_match.group(2))
      if distance is None:
        continue
      ref_match = re.search(r"from\s+(?:point\s+)?([A-Z])", snippet, re.I)
      ref_letter = ref_match.group(1) if ref_match else None
      pos = resolve_distance(distance, ref_letter, snippet)
      add_support(pos, f"Bearing {len(inputs['supports']) + 1}")
  for letter in support_letter_hits:
    add_support(resolve_letter(letter), f"Bearing {letter}")

  inputs["supports"].sort(key=lambda s: s["x"])

  def axis_and_sign(snippet_lower: str):
    axis = "z"
    sign = -1.0
    if "upward" in snippet_lower or "upwards" in snippet_lower or "up" in snippet_lower:
      axis = "z"
      sign = 1.0
    if "downward" in snippet_lower or "down" in snippet_lower:
      axis = "z"
      sign = -1.0
    if any(word in snippet_lower for word in ("horizontal", "radial", "side", "lateral")):
      axis = "y"
      if "to the right" in snippet_lower or "rightward" in snippet_lower or "toward the right" in snippet_lower:
        sign = 1.0
      elif "to the left" in snippet_lower or "leftward" in snippet_lower:
        sign = -1.0
      else:
        sign = -1.0
    if "vertical" in snippet_lower:
      axis = "z"
    return axis, sign

  # Gear loads
  for gear_match in re.finditer(r"\bgear\b", text, re.I):
    gear_start = gear_match.start()
    snippet_start = max(0, gear_start - 40)
    snippet_end = min(len(text), gear_start + 200)
    snippet_full = text[snippet_start:snippet_end]

    def find_force(keyword: str):
      keyword_re = re.escape(keyword)
      force_pattern = re.compile(rf"(?P<val>{NUM})\s*(?P<unit>kN|N|lb|lbf)", re.I)
      keyword_lower = keyword.lower()
      other_keyword = None
      if keyword_lower == "tangential":
        other_keyword = "radial"
      elif keyword_lower == "radial":
        other_keyword = "tangential"
      best_after = None
      best_before = None
      for kw_match in re.finditer(keyword_re, snippet_full, re.I):
        idx = kw_match.start()
        window_start = max(0, idx - 80)
        window_end = min(len(snippet_full), idx + 80)
        for fc in force_pattern.finditer(snippet_full, window_start, window_end):
          val = safe_float(fc.group("val"))
          unit = fc.group("unit")
          if val is None or unit is None:
            continue
          distance = abs(fc.start() - idx)
          if fc.start() >= idx:
            between = snippet_full[idx:fc.start()].lower()
            if other_keyword and other_keyword in between:
              continue
            if best_after is None or distance < best_after[0]:
              best_after = (distance, val, unit)
          else:
            between = snippet_full[fc.end():idx].lower()
            if other_keyword and other_keyword in between:
              continue
            if best_before is None or distance < best_before[0]:
              best_before = (distance, val, unit)
      if best_after is not None and best_before is not None:
        if best_after[0] <= best_before[0] + 5:
          candidate = best_after
        else:
          candidate = best_before
      elif best_after is not None:
        candidate = best_after
      else:
        candidate = best_before
      if candidate:
        return unit_to_force(candidate[1], candidate[2])
      return None

    Ft = find_force("tangential")
    Fr = find_force("radial") or 0.0

    loc_letter = None
    pos = None
    gear_idx = gear_start - snippet_start
    matches_at = list(re.finditer(r"at\s+(?:point\s+)?([A-Z])", snippet_full, re.I))
    if matches_at:
      ordered = sorted(matches_at, key=lambda m: abs(m.start() - gear_idx)) if gear_idx != -1 else matches_at
      for candidate_match in ordered:
        letter_candidate = candidate_match.group(1).upper()
        if abs(candidate_match.start() - gear_idx) > 60:
          continue
        pos_candidate = resolve_letter(letter_candidate)
        if pos_candidate is not None:
          loc_letter = letter_candidate
          pos = pos_candidate
          break
    if loc_letter is None and gear_idx != -1:
      before_section = snippet_full[:gear_idx]
      m = re.search(r"(?:point\s+)?([A-Z])[^A-Z]*$", before_section, re.I)
      if m:
        letter_candidate = m.group(1).upper()
        pos_candidate = resolve_letter(letter_candidate)
        if pos_candidate is not None:
          loc_letter = letter_candidate
          pos = pos_candidate

    if pos is None and loc_letter:
      pos = resolve_letter(loc_letter)

    if pos is None:
      for dist_match in re.finditer(r"(" + NUM + r")\s*(mm|cm|m|in|ft)\s*(?:from\s+(?:point\s+)?([A-Z]))?", snippet_full, re.I):
        matched_text = dist_match.group(0).lower()
        if "from" not in matched_text and not dist_match.group(3):
          continue
        dist_val = unit_to_m(safe_float(dist_match.group(1)), dist_match.group(2))
        pos_candidate = resolve_distance(dist_val, dist_match.group(3), snippet_full)
        if pos_candidate is not None:
          pos = pos_candidate
          break
    radius = None
    best_radius_after = None
    best_radius_before = None
    for r_match in re.finditer(r"(?:pitch\s+(?:diameter|radius)|radius|pitch)\s*(?:=|of)?\s*(" + NUM + r")\s*(mm|cm|m|in)", snippet_full, re.I):
      r_val = unit_to_m(safe_float(r_match.group(1)), r_match.group(2))
      if r_val is None:
        continue
      if "diameter" in r_match.group(0).lower():
        r_val = r_val / 2.0
      dist_here = abs(r_match.start() - gear_idx)
      if r_match.start() >= gear_idx:
        if best_radius_after is None or dist_here < best_radius_after[0]:
          best_radius_after = (dist_here, r_val)
      else:
        if best_radius_before is None or dist_here < best_radius_before[0]:
          best_radius_before = (dist_here, r_val)
    if best_radius_after:
      radius = best_radius_after[1]
    elif best_radius_before:
      radius = best_radius_before[1]
    if Ft is None or pos is None:
      unresolved_notes.append("gear load")
      continue
    load_entry = {"type": "gear", "x": pos, "F_t": Ft, "F_r": Fr or 0.0}
    if radius:
      load_entry["r"] = radius
    inputs["loads"].append(load_entry)

  # Distributed loads
  distributed_pattern = re.compile(r"(?:uniform|distributed).{0,200}", re.I | re.S)
  for match in distributed_pattern.finditer(text):
    phrase = match.group(0)
    snippet = text[max(0, match.start() - 80):min(len(text), match.end() + 80)]
    q_match = re.search(r"(" + NUM + r")\s*(kN/m|N/m|kN/mm|N/mm|lb/ft|lb/in|lbf/ft|lbf/in)", phrase, re.I)
    if not q_match:
      continue
    q_val = unit_to_line_force(safe_float(q_match.group(1)), q_match.group(2))
    start = end = None
    span_letters = re.search(
      r"(?:between|from)\s+(?:point\s+)?([A-Z])\s*(?:and|to)\s*(?:point\s+)?([A-Z])",
      snippet,
      re.I
    )
    if span_letters:
      letter1 = span_letters.group(1).upper()
      letter2 = span_letters.group(2).upper()
      start = resolve_letter(letter1)
      end = resolve_letter(letter2)
    if start is None or end is None:
      letters = [ltr.upper() for ltr in re.findall(r"\b([A-Z])\b", snippet)]
      anchors: List[Tuple[str, float]] = []
      seen_letters = set()
      for letter in letters:
        if letter in seen_letters:
          continue
        pos_letter = resolve_letter(letter)
        if pos_letter is not None:
          anchors.append((letter, pos_letter))
          seen_letters.add(letter)
        if len(anchors) >= 2:
          break
      if start is None and len(anchors) >= 1:
        start = anchors[0][1]
      if end is None and len(anchors) >= 2:
        end = anchors[1][1]
    if start is None or end is None:
      span_match = re.search(r"(" + NUM + r")\s*(mm|cm|m|in|ft)\s*(?:and|to|-)\s*(" + NUM + r")\s*(mm|cm|m|in|ft)", snippet, re.I)
      if span_match:
        start = unit_to_m(safe_float(span_match.group(1)), span_match.group(2))
        end = unit_to_m(safe_float(span_match.group(3)), span_match.group(4))
    if q_val is None or start is None or end is None:
      unresolved_notes.append("distributed load")
      continue
    if end < start:
      start, end = end, start
    axis, sign = axis_and_sign(phrase.lower())
    load_entry = {"type": "distributed", "start": start, "end": end}
    if axis == "y":
      load_entry["q_y"] = sign * q_val
    else:
      load_entry["q_z"] = sign * q_val
    inputs["loads"].append(load_entry)

  # Point loads at named points
  point_pattern = re.compile(
    r"(" + NUM + r")\s*(kN|N|lb|lbf)(?:[^0-9]{0,160}?)(?:at|applied at|acting at|acts at)\s+(?:point\s+)?([A-Z])",
    re.I | re.S
  )
  for match in point_pattern.finditer(text):
    magnitude = unit_to_force(safe_float(match.group(1)), match.group(2))
    letter = match.group(3)
    pos = resolve_letter(letter)
    snippet_full = text[match.start():match.end()]
    snippet = snippet_full.lower()
    if letter and letter.upper() not in node_positions and any(
      keyword in snippet for keyword in ("midspan", "mid span", "midpoint", "center", "centre", "middle")
    ):
      continue
    context_before = text[max(0, match.start() - 40):match.start()].lower()
    if any(keyword in context_before for keyword in ("gear", "tangential", "torque", "moment", "couple")):
      continue
    axis, sign = axis_and_sign(snippet)
    if magnitude is None or pos is None:
      if any(keyword in snippet for keyword in ("midspan", "mid span", "midpoint", "center", "centre", "middle")):
        continue
      unresolved_notes.append(f"point load at {letter}")
      continue
    entry = {"type": "point_force", "x": pos}
    if axis == "y":
      entry["Fy"] = sign * magnitude
    else:
      entry["Fz"] = sign * magnitude
    inputs["loads"].append(entry)

  # Point loads by distance
  point_numeric_pattern = re.compile(
    r"(" + NUM + r")\s*(kN|N|lb|lbf).{0,200}?(?:at|applied at|acting at|acts at|located at)\s*(?:a\s*distance\s*of\s*)?(" + NUM + r")\s*(mm|cm|m|in|ft)",
    re.I | re.S
  )
  for match in point_numeric_pattern.finditer(text):
    snippet = match.group(0)
    snippet_lower = snippet.lower()
    context_before = text[max(0, match.start() - 40):match.start()].lower()
    if any(keyword in context_before for keyword in ("torque", "moment", "gear", "tangential", "couple")):
      continue
    if re.search(r"point\s+[A-Z]\b", snippet, re.I):
      continue  # already handled
    magnitude = unit_to_force(safe_float(match.group(1)), match.group(2))
    dist_val = unit_to_m(safe_float(match.group(3)), match.group(4))
    ref_match = re.search(r"from\s+(?:point\s+)?([A-Z])", snippet, re.I)
    pos = resolve_distance(dist_val, ref_match.group(1) if ref_match else None, snippet)
    axis, sign = axis_and_sign(snippet.lower())
    if magnitude is None or pos is None:
      unresolved_notes.append("point load by distance")
      continue
    entry = {"type": "point_force", "x": pos}
    if axis == "y":
      entry["Fy"] = sign * magnitude
    else:
      entry["Fz"] = sign * magnitude
    inputs["loads"].append(entry)

  midspan_pattern = re.compile(
    r"(?:point\s+load|load)\s+of\s+(" + NUM + r")\s*(kN|N|lb|lbf)[^\.]{0,160}?(?:at|acting at|placed at)\s*(mid[- ]?span|midpoint|center|centre|middle)",
    re.I
  )
  for match in midspan_pattern.finditer(text):
    magnitude = unit_to_force(safe_float(match.group(1)), match.group(2))
    if magnitude is None:
      continue
    if total_length <= 0:
      unresolved_notes.append("point load at midspan (length unknown)")
      continue
    x_mid = total_length / 2.0
    snippet = text[match.start():min(len(text), match.end() + 40)].lower()
    axis, sign = axis_and_sign(snippet)
    entry = {"type": "point_force", "x": x_mid}
    if axis == "y":
      entry["Fy"] = sign * magnitude
    else:
      entry["Fz"] = sign * magnitude
    inputs["loads"].append(entry)

  # Component weights
  weight_pattern = re.compile(r"(?:weight|mass)\s+of\s+(" + NUM + r")\s*(kN|N|lb|lbf).{0,120}?at\s+(?:point\s+)?([A-Z])", re.I | re.S)
  for match in weight_pattern.finditer(text):
    force = unit_to_force(safe_float(match.group(1)), match.group(2))
    pos = resolve_letter(match.group(3))
    if force is None or pos is None:
      unresolved_notes.append("component weight")
      continue
    inputs["loads"].append({"type": "component_weight", "x": pos, "W": force})

  # Torques
  torque_pattern = re.compile(r"torque.{0,200}", re.I | re.S)
  for match in torque_pattern.finditer(text):
    snippet = match.group(0)
    T_match = re.search(
      r"(" + NUM + r")\s*(kN\*m|kN·m|N\*m|N·m|lb\*ft|lbf\*ft|ft\*lb|ft\*lbf|in\*lb|in\*lbf)",
      snippet,
      re.I
    )
    if not T_match:
      continue
    torque = unit_to_torque(safe_float(T_match.group(1)), T_match.group(2))
    loc_letter_match = re.search(r"at\s+(?:point\s+)?([A-Z])", snippet, re.I)
    pos = resolve_letter(loc_letter_match.group(1)) if loc_letter_match else None
    if pos is None:
      dist_match = re.search(r"(" + NUM + r")\s*(mm|cm|m|in|ft)\s*(?:from\s+(?:point\s+)?([A-Z]))?", snippet, re.I)
      if dist_match:
        pos = resolve_distance(unit_to_m(safe_float(dist_match.group(1)), dist_match.group(2)), dist_match.group(3), snippet)
    if pos is None:
      pos = total_length
    if torque is not None:
      inputs["loads"].append({"type": "torque", "x": pos, "T": torque})

  G = parse_value_unit(text, r"(?:shear modulus|G\b)", ["Pa", "kPa", "MPa", "GPa", "psi"])
  if G:
    inputs["material"]["G"] = G.__dict__
  Sut = parse_value_unit(text, r"(?:ultimate tensile strength|S[_\s]?ut|Sut)", ["Pa", "kPa", "MPa", "GPa", "psi"])
  if Sut:
    inputs["material"]["S_ut"] = Sut.__dict__
  Sy = parse_value_unit(text, r"(?:yield strength|S[_\s]?y|Sy)", ["Pa", "kPa", "MPa", "GPa", "psi"])
  if Sy:
    inputs["material"]["S_y"] = Sy.__dict__

  if not inputs["segments"]:
    warnings.append("Unable to parse shaft segments; please provide segments manually.")

  if inputs["segments"] and not inputs["supports"]:
    add_support(0.0, "Bearing A")
    add_support(total_length, "Bearing B")
    warnings.append("Assuming supports at shaft ends (0 and L). Adjust if needed.")
  elif not inputs["supports"]:
    warnings.append("Unable to parse support locations; please provide supports manually.")

  if not inputs["loads"]:
    warnings.append("Unable to parse shaft loads; please provide loads manually.")
  else:
    filtered_notes = []
    midspan_present = re.search(r"\bmid[- ]?span\b|\bmidpoint\b|\bcentre\b|\bcenter\b|\bmiddle\b", text, re.I)
    for note in unresolved_notes:
      if not note:
        continue
      if note.startswith("point load at "):
        letter = note[len("point load at "):].strip()
        if letter.upper() not in node_positions and midspan_present:
          continue
      filtered_notes.append(note)
    unresolved_clean = sorted(set(filtered_notes))
    if unresolved_clean:
      warnings.append("Skipped loads due to missing context: " + ", ".join(unresolved_clean))

  return inputs, outputs, warnings

def extract_spring_torsion(text:str):
  inputs={"geometry":{}, "material":{}, "loads":{}}
  d = parse_value_unit(text, r"(?:wire diameter|wire dia|d\b)", ["mm","cm","m","in"])
  if d: inputs["geometry"]["d"]=d.__dict__
  D = parse_value_unit(text, r"(?:mean coil diameter|mean diameter|D\b)", ["mm","cm","m","in"])
  if D: inputs["geometry"]["D"]=D.__dict__
  na_match = re.search(rf"(?:active coils|turns)\s*(?:=)?\s*({NUM})", text, re.I)
  if na_match:
    val = safe_float(na_match.group(1))
    unitless = make_unitless(val)
    if unitless: inputs["geometry"]["n_a"]=unitless
  G = parse_value_unit(text, r"(?:shear modulus|G)", ["Pa","kPa","MPa","GPa","psi"])
  if G: inputs["material"]["G"]=G.__dict__
  M = parse_value_unit(text, r"(?:torque|moment|M)", ["N*m","N·m","kN*m"])
  if M: inputs["loads"]["M"]=M.__dict__
  outputs=[]
  add_output(outputs,"k_theta","N*m/rad")
  add_output(outputs,"theta","rad")
  add_output(outputs,"sigma_max","MPa")
  add_output(outputs,"Wahl_factor")
  return inputs, outputs

def extract_spring_concentric(text:str):
  inputs={"springs":{"spring1":{"geometry":{}, "material":{}}, "spring2":{"geometry":{}, "material":{}}}, "loads":{}}
  common_units = ["mm","cm","m","in"]
  # Inner spring
  d1 = parse_value_unit(text, r"(?:inner spring wire diameter|inner wire|d1)", common_units)
  if d1: inputs["springs"]["spring1"]["geometry"]["d"]=d1.__dict__
  D1 = parse_value_unit(text, r"(?:inner spring mean diameter|inner mean diameter|D1)", common_units)
  if D1: inputs["springs"]["spring1"]["geometry"]["D"]=D1.__dict__
  n1 = re.search(rf"(?:inner (?:active )?coils|n1)\s*(?:=)?\s*({NUM})", text, re.I)
  if n1:
    val = safe_float(n1.group(1))
    unitless = make_unitless(val)
    if unitless: inputs["springs"]["spring1"]["geometry"]["n_a"]=unitless
  G1 = parse_value_unit(text, r"(?:inner shear modulus|G1)", ["Pa","kPa","MPa","GPa","psi"])
  if G1: inputs["springs"]["spring1"]["material"]["G"]=G1.__dict__

  # Outer spring
  d2 = parse_value_unit(text, r"(?:outer spring wire diameter|outer wire|d2)", common_units)
  if d2: inputs["springs"]["spring2"]["geometry"]["d"]=d2.__dict__
  D2 = parse_value_unit(text, r"(?:outer spring mean diameter|outer mean diameter|D2)", common_units)
  if D2: inputs["springs"]["spring2"]["geometry"]["D"]=D2.__dict__
  n2 = re.search(rf"(?:outer (?:active )?coils|n2)\s*(?:=)?\s*({NUM})", text, re.I)
  if n2:
    val = safe_float(n2.group(1))
    unitless = make_unitless(val)
    if unitless: inputs["springs"]["spring2"]["geometry"]["n_a"]=unitless
  G2 = parse_value_unit(text, r"(?:outer shear modulus|G2)", ["Pa","kPa","MPa","GPa","psi"])
  if G2: inputs["springs"]["spring2"]["material"]["G"]=G2.__dict__

  F_total = parse_value_unit(text, r"(?:total load|combined load|F_total)", ["N","kN"])
  if F_total:
    inputs["loads"]["F_total"]=F_total.__dict__
  outputs=[]
  add_output(outputs,"k_total","N/m")
  add_output(outputs,"deflection","mm")
  add_output(outputs,"F_spring1","N")
  add_output(outputs,"F_spring2","N")
  add_output(outputs,"load_share_spring1")
  add_output(outputs,"load_share_spring2")
  return inputs, outputs

def build_spec(text:str)->Dict[str,Any]:
  text = normalize_text(text).replace("'","'").replace("-","-").replace("-","-")
  cls, conf = classify(text)
  inputs={}; outputs=[]; assumptions=[]; ambiguities=[]
  if cls=="beam.eb.simply_supported.udl":
    inputs, outputs = extract_beam_udl(text)
    assumptions += ["small_deflection","plane_sections_remain_plane"]
  elif cls=="pv.cylinder.thin":
    inputs, outputs = extract_pv_cylinder(text)
    try:
      Rsi = inputs.get("geometry",{}).get("R",{}).get("si")
      tsi = inputs.get("geometry",{}).get("t",{}).get("si")
      if Rsi and tsi and (tsi/Rsi) >= 0.1:
        ambiguities.append({"field":"thin_wall","reason":"t/R >= 0.1","suggestions":["Use thick-wall theory","Reduce thickness ratio"]})
      else:
        assumptions.append("thin_wall")
    except: pass
  elif cls=="column.euler.buckling":
    inputs, outputs = extract_column_buckling(text)
  elif cls=="bearing.ball.life_reliability":
    inputs, outputs = extract_bearing_life(text)
  elif cls=="bearing.ball.required_C":
    inputs, outputs = extract_bearing_required_rating(text)
  elif cls=="bearing.ball.equivalent_load":
    inputs, outputs = extract_bearing_equivalent(text)
  elif cls=="shaft.analysis.segmented":
    inputs, outputs, warnings = extract_shaft_segmented(text)
    for msg in warnings:
      ambiguities.append({"field":"shaft", "reason": msg, "suggestions":["Adjust input manually in JSON panel"]})
  elif cls=="spring.helical.compression":
    inputs, outputs = extract_spring_helical(text, mode="compression")
  elif cls=="spring.helical.extension":
    inputs, outputs = extract_spring_helical(text, mode="extension")
  elif cls=="spring.helical.torsion":
    inputs, outputs = extract_spring_torsion(text)
  elif cls=="spring.helical.parallel":
    inputs, outputs = extract_spring_concentric(text)
  elif cls=="shaft.torsion.solid":
    inputs, outputs = extract_torsion_solid(text)
  elif cls=="power.screw.raise":
    inputs, outputs, warnings = extract_power_screw(text)
    for msg in warnings:
      ambiguities.append({"field": "power_screw", "reason": msg, "suggestions": ["Specify missing value in JSON panel"]})
  elif cls=="clutch.single_disc.uniform_wear":
    inputs, outputs, warnings = extract_disc_brake_uniform_wear(text)
    for msg in warnings:
      ambiguities.append({"field": "disc_brake", "reason": msg, "suggestions": ["Specify missing value in JSON panel"]})
  elif cls=="clutch.single_disc.uniform_pressure":
    inputs, outputs, warnings = extract_disc_brake_uniform_pressure(text)
    for msg in warnings:
      ambiguities.append({"field": "disc_brake", "reason": msg, "suggestions": ["Specify missing value in JSON panel"]})
  elif cls=="belt.flat.power":
    inputs, outputs, warnings = extract_belt_power(text)
    for msg in warnings:
      ambiguities.append({"field": "belt", "reason": msg, "suggestions": ["Specify missing value in JSON panel"]})
  elif cls=="belt.flat.tension_ratio":
    inputs, outputs, warnings = extract_belt_tension_ratio(text)
    for msg in warnings:
      ambiguities.append({"field": "belt", "reason": msg, "suggestions": ["Specify missing value in JSON panel"]})
  elif cls=="dyn.sdof.base_excited.harmonic":
    inputs, outputs = extract_sdof_base(text)
  else:
    inputs, outputs = extract_beam_udl(text)  # best-effort fallback
    cls="beam.eb.simply_supported.udl"; conf=0.5
    ambiguities.append({"field":"class","reason":"low confidence","suggestions":["Specify problem type explicitly"]})
  return {
    "class": cls,
    "confidence": round(conf,3),
    "inputs": inputs,
    "outputs": outputs,
    "assumptions": assumptions,
    "ambiguities": ambiguities
  }
