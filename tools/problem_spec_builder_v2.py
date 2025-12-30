#!/usr/bin/env python3
"""
problem_spec_builder_v2.py — robust baseline parser for textbook problems (Phase‑1).
Usage:
  python problem_spec_builder_v2.py --text "..." --out spec.json
  python problem_spec_builder_v2.py --in path/to/problem.txt --out spec.json
"""
import argparse, re, json, math
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

UNIT2SI = {
  "m": ("Length", 1.0), "meter":("Length",1.0), "meters":("Length",1.0),
  "mm": ("Length", 1e-3), "cm":("Length",1e-2), "in":("Length",0.0254), "ft":("Length",0.3048),
  "m^2":("Area",1.0), "mm^2":("Area",1e-6), "in^2":("Area",0.00064516),
  "m^4":("Inertia",1.0), "mm^4":("Inertia",1e-12), "in^4":("Inertia",4.162314e-7),
  "n":("Force",1.0), "kn":("Force",1e3), "lbf":("Force",4.4482216152605),
  "n/m":("Force/Length",1.0), "kn/m":("Force/Length",1e3), "lbf/ft":("Force/Length",4.4482216152605/0.3048),
  "pa":("Pressure",1.0), "kpa":("Pressure",1e3), "mpa":("Pressure",1e6), "gpa":("Pressure",1e9), "psi":("Pressure",6894.757293168),
  "kg":("Mass",1.0), "lbm":("Mass",0.45359237),
  "n·s/m":("ViscDamp",1.0), "n*s/m":("ViscDamp",1.0),
  "m/s^2":("Accel",1.0), "g":("Accel",9.81),
  "hz":("Freq",1.0),
  "k":("Temp",1.0), "°c":("Temp",1.0)
}
NUM = r"(?:\d+(?:\.\d+)?(?:e[+\-]?\d+)?)"; UN_BY=r"(?:by|x|×)"; SP=r"[ \t]+"

def norm_unit(u:str)->str:
  u = (u or "").strip().lower().replace("·","*").replace(" ","")
  return u.replace("*","·")

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
  ualt = "|".join(map(re.escape, units))
  pat = rf"(?:{key_pattern})[^0-9a-zA-Z]*({NUM})\s*({ualt})"
  m = re.search(pat, text, re.I)
  if not m: return None
  val = safe_float(m.group(1)); unit = m.group(2) if len(m.groups())>=2 else None
  if val is None or unit is None: return None
  return make_qty(val, unit)

def parse_single_num_unit(text:str, key_pattern:str, units:List[str])->Optional[Quantity]:
  ualt = "|".join(map(re.escape, units))
  pat1 = rf"(?:{key_pattern})[^0-9a-zA-Z]*({NUM})\s*({ualt})"
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
  ualt = "|".join(map(re.escape, units))
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
      val = safe_float(m2.group(0))
      if val is not None:
        inputs["material"]["nu"]={"value":val,"unit":"-","dim":"None","si":val}
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
  t = parse_value_unit(text, r"(?:thickness|wall thickness|t)", ["m","mm","in"])
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
        val = safe_float(m2.group(0))
        if val is not None:
            inputs["system"]["zeta"]={"value":val,"unit":"-","dim":"None","si":val}
  a0 = parse_value_unit(text, r"(?:base acceleration|acceleration)", ["m/s^2","g"])
  f = parse_value_unit(text, r"(?:frequency|f)", ["Hz"])
  if a0: inputs["excitation"]["a0"]=a0.__dict__
  if f: inputs["excitation"]["f"]=f.__dict__
  outputs=[{"metric":"x_peak","unit_pref":"mm"}]
  return inputs, outputs

def build_spec(text:str)->Dict[str,Any]:
  text = text.replace("’","'").replace("–","-").replace("—","-")
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

def main():
  ap = argparse.ArgumentParser(description="ProblemSpec builder v2")
  ap.add_argument("--in", dest="infile", type=str, help="Path to text file")
  ap.add_argument("--text", dest="text", type=str, help="Raw problem text (overrides --in)")
  ap.add_argument("--out", dest="outfile", type=str, required=True, help="Output JSON path")
  args = ap.parse_args()
  if args.text:
    txt = args.text
  elif args.infile:
    with open(args.infile,"r",encoding="utf-8",errors="ignore") as f:
      txt = f.read()
  else:
    raise SystemExit("Provide --text \"...\" or --in file.txt, and --out spec.json")
  spec = build_spec(txt)
  with open(args.outfile,"w",encoding="utf-8") as f:
    json.dump(spec,f,indent=2)
  print(f"Wrote ProblemSpec → {args.outfile} (class={spec['class']} conf={spec['confidence']})")

if __name__=="__main__":
  main()