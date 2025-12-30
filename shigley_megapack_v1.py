# shigley_megapack_v1.py — ALL-IN-ONE (Streamlit)
# Run:  pip install streamlit  &&  streamlit run shigley_megapack_v1.py
import math, re, json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

st.set_page_config(page_title="Shigley MegaPack — Parse + Solve", page_icon="🛠️", layout="wide")

# ================= Units & helpers ================
UNIT2SI = {
  "m":("L",1.0),"mm":("L",1e-3),"cm":("L",1e-2),"in":("L",0.0254),"ft":("L",0.3048),
  "pa":("P",1.0),"kpa":("P",1e3),"mpa":("P",1e6),"gpa":("P",1e9),"psi":("P",6894.757293168),
  "n":("F",1.0),"kn":("F",1e3),"lbf":("F",4.4482216152605),
  "n/m":("FL-1",1.0),"kn/m":("FL-1",1e3),"lbf/ft":("FL-1",4.4482216152605/0.3048),
  "m^4":("I",1.0),"mm^4":("I",1e-12),"in^4":("I",4.162314e-7),
  "m^2":("A",1.0),"mm^2":("A",1e-6),"in^2":("A",0.00064516),
  "hz":("f",1.0)
}
def norm_unit(u:str)->str: return (u or "").strip().lower().replace("·","*").replace(" ","")
@dataclass
class Quantity:
  value: float; unit: str; dim: str; si: float
def make_qty(val: float, ustr: str)->Optional[Quantity]:
  u = norm_unit(ustr); 
  if u in UNIT2SI:
    dim,k = UNIT2SI[u]; return Quantity(val, ustr, dim, val*k)
  return None
def to_si(q, default=None):
  if isinstance(q, dict):
    if "si" in q:
      try: return float(q["si"])
      except: return default
    if "value" in q:
      try: return float(q["value"])
      except: return default
    return default
  try: return float(q)
  except: return default
def ensure(v, name):
  if v is None or (isinstance(v,float) and math.isnan(v)): raise ValueError(f"Missing required input: {name}")
  return v
def I_rect(b,h): return b*h**3/12.0

# Engineering formatting
UNIT_PREFS = {
  "delta":"mm","delta_mid":"mm","deflection":"mm",
  "sigma":"MPa","sigma_bending_max":"MPa","sigma_hoop":"MPa","sigma_longitudinal":"MPa","sigma_eq":"MPa","tau":"MPa","tau_max":"MPa",
  "M":"N·m","M_max":"N·m","T":"N·m","T_total":"N·m","T_thread":"N·m","T_collar":"N·m",
  "reaction_left":"kN","reaction_right":"kN","R_support":"kN","P_cr":"kN","P_cr_johnson":"kN",
  "k":"N/m","J":"m^4","L10_rev":"rev","L10_hours":"hours","contact_pressure":"MPa"
}
def fmt_eng(value_si: float, pref: Optional[str])->Tuple[float,str]:
  u = (pref or "").lower(); conv=1.0; lab=pref or "(SI)"
  if u=="mm": conv=1e3; lab="mm"
  elif u=="mpa": conv=1e-6; lab="MPa"
  elif u=="kpa": conv=1e-3; lab="kPa"
  elif u=="pa": conv=1.0; lab="Pa"
  elif u=="kn": conv=1e-3; lab="kN"
  elif u in ("n·m","n*m"): conv=1.0; lab="N·m"
  elif u=="kn·m": conv=1e-3; lab="kN·m"
  elif u=="hz": conv=1.0; lab="Hz"
  elif u=="deg": conv=180.0/math.pi; lab="deg"
  return value_si*conv, lab
def pick_unit_pref(key:str): return UNIT_PREFS.get(key)

# ================= Parser (Phase-1 robust core) =================
NUM = r"(?:\d+(?:\.\d+)?(?:e[+\-]?\d+)?)"; UN_BY=r"(?:by|x|×)"; SP=r"[ \t]+"
def parse_value_unit(text:str, key_pat:str, units:List[str])->Optional[Quantity]:
  ualt = "|".join(map(re.escape, units)); m = re.search(rf"(?:{key_pat})(?:[^0-9]*?)({NUM})\s*({ualt})", text, re.I)
  if not m: return None
  try: return make_qty(float(m.group(1)), m.group(2))
  except: return None
def parse_single_num_unit(text:str, key_pat:str, units:List[str])->Optional[Quantity]:
  ualt = "|".join(map(re.escape, units))
  m = re.search(rf"(?:{key_pat})(?:[^0-9]*?)({NUM})\s*({ualt})", text, re.I)
  if not m: m = re.search(rf"({NUM})\s*({ualt}).{{0,40}}(?:{key_pat})", text, re.I)
  if not m: return None
  try: return make_qty(float(m.group(1)), m.group(2))
  except: return None
def parse_rect_section(text:str):
  m = re.search(rf"({NUM})\s*(mm|cm|m|in){SP}?(?:{UN_BY}){SP}?({NUM})\s*(mm|cm|m|in)", text, re.I)
  if not m: return None
  b = make_qty(float(m.group(1)), m.group(2)); h = make_qty(float(m.group(3)), m.group(4))
  if not b or not h: return None
  return (b,h)
def contains_any(text:str, words:List[str])->bool:
  return any(re.search(rf"\b{re.escape(w)}\b", text, re.I) for w in words)
def classify(text:str):
  cand=[]
  s=0.0
  if contains_any(text,["simply supported","pinned and roller","pinned-roller"]): s+=0.4
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
  if re.search(r"\bcolumn|effective length factor|K\s*=\b", text, re.I): s+=0.3
  cand.append(("column.euler", s))
  best=max(cand,key=lambda x:x[1]); return best[0], min(1.0,max(0.0,best[1]))
def build_inputs_beam_udl(text:str):
  inputs={"geometry":{}, "material":{}, "loads":[], "supports":[]}
  L = parse_single_num_unit(text, r"(?:span|length|L)", ["m","mm","cm","in","ft"])
  if L: inputs["geometry"]["L"]=L.__dict__
  sec = parse_rect_section(text)
  if sec:
    b,h=sec; inputs["geometry"]["section"]={"shape":"rect","b":b.__dict__,"h":h.__dict__}
  E = parse_value_unit(text, r"(?:E|Young(?:'s)? modulus|modulus)", ["Pa","MPa","GPa","psi"])
  if E: inputs["material"]["E"]=E.__dict__
  q = parse_value_unit(text, r"(?:uniformly distributed load|distributed load|udl|q|w0)", ["N/m","kN/m","lbf/ft"])
  if q: inputs["loads"].append({"type":"uniform","q":q.__dict__,"region":"span","direction":"-y"})
  if re.search(r"\bsimply supported|pinned and roller|pinned-roller\b", text, re.I):
    inputs["supports"]=[{"type":"pinned","at":"x=0"},{"type":"roller","at":"x=L"}]
  return inputs
def build_inputs_pv_thin(text:str):
  inputs={"geometry":{}, "material":{}, "loads":[], "supports":[]}
  R = parse_value_unit(text, r"(?:radius|R)", ["m","mm","in"]);  t = parse_value_unit(text, r"(?:thickness|wall thickness|t)", ["m","mm","in"])
  if R: inputs["geometry"]["R"]=R.__dict__
  if t: inputs["geometry"]["t"]=t.__dict__
  p = parse_value_unit(text, r"(?:internal pressure|pressure|p)", ["Pa","kPa","MPa","psi"])
  if p: inputs["loads"].append({"type":"pressure","p":p.__dict__})
  return inputs
SUPERSCRIPT_MAP = str.maketrans({
  "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
  "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
  "⁻": "-", "⁺": "+", "·": "x", "∙": "x", "×": "x"
})

def normalize_text(text: str) -> str:
  t = text.translate(SUPERSCRIPT_MAP)
  t = t.replace("×", "x")
  def repl(match):
    coeff = match.group(1)
    exp = match.group(2)
    return f"{coeff}e{exp}"
  t = re.sub(r"(\d+(?:\.\d+)?)\s*(?:[x\*])\s*10\s*(?:\^)?\s*([+\-]?\d+)", repl, t, flags=re.I)
  t = re.sub(r"\b(mm|cm|m|in)(\d+)", lambda m: f"{m.group(1)}^{m.group(2)}", t, flags=re.I)
  return t

def build_spec(text:str)->Dict[str,Any]:
  text = normalize_text(text).replace("'","'").replace("-","-").replace("-","-")
  cls, conf = classify(text); inputs={}; outputs=[]; assumptions=[]; ambiguities=[]
  if cls=="beam.eb.simply_supported.udl":
    inputs = build_inputs_beam_udl(text); outputs=[{"metric":"delta_mid","unit_pref":"mm"},{"metric":"sigma_bending_max","unit_pref":"MPa"}]
    assumptions+=["small_deflection","plane_sections_remain_plane"]
  elif cls=="pv.cylinder.thin":
    inputs = build_inputs_pv_thin(text); outputs=[{"metric":"sigma_hoop","unit_pref":"MPa"},{"metric":"sigma_longitudinal","unit_pref":"MPa"}]; assumptions.append("thin_wall")
  elif cls=="column.euler":
    inputs={"geometry":{},"material":{},"loads":[]}; outputs=[{"metric":"P_cr","unit_pref":"kN"}]
  else:
    inputs = build_inputs_beam_udl(text); outputs=[{"metric":"delta_mid","unit_pref":"mm"}]; ambiguities.append({"field":"class","reason":"low confidence"})
  return {"class":cls,"confidence":round(conf,3),"inputs":inputs,"outputs":outputs,"assumptions":assumptions,"ambiguities":ambiguities}




# ================= Solvers (broad set) =================
def solve_beam_udl(spec):
  inp=spec.get("inputs",{}); geom=inp.get("geometry",{}); mat=inp.get("material",{}); loads=inp.get("loads",[])
  L=to_si(geom.get("L")); E=to_si(mat.get("E")); sec=geom.get("section",{})
  I=to_si(sec.get("I")); 
  if I is None and "b" in sec and "h" in sec: I=I_rect(to_si(sec["b"]), to_si(sec["h"]))
  q=None
  for ld in loads:
    if ld.get("type")=="uniform": q=to_si(ld.get("q")); break
  if None in (L,E,I,q): return {}
  delta_mid=5*q*L**4/(384*E*I); Mmax=q*L**2/8.0; h=to_si(sec.get("h"))
  res={"delta_mid":delta_mid,"M_max":Mmax,"reaction_left":q*L/2.0,"reaction_right":q*L/2.0}
  if h is not None: res["sigma_bending_max"]=Mmax*(h/2.0)/I
  return res

def solve_pv_thin(spec):
  inp=spec.get("inputs",{}); geom=inp.get("geometry",{}); loads=inp.get("loads",[])
  R=to_si(geom.get("R")); t=to_si(geom.get("t")); p=None
  for ld in loads:
    if ld.get("type")=="pressure": p=to_si(ld.get("p")); break
  if None in (R,t,p): return {}
  return {"sigma_hoop":p*R/t,"sigma_longitudinal":p*R/(2*t)}

def solve_pv_thick(inputs):
  ri=to_si(inputs.get("geometry",{}).get("r_i")); ro=to_si(inputs.get("geometry",{}).get("r_o"))
  pi=to_si(inputs.get("loads",{}).get("p_i")); po=to_si(inputs.get("loads",{}).get("p_o")) or 0.0
  if None in (ri,ro,pi): return {}
  A=(pi*ri**2 - po*ro**2)/(ro**2 - ri**2); B=(ri**2*ro**2*(po - pi))/(ro**2 - ri**2)
  return {"sigma_r_ri":A - B/ri**2,"sigma_t_ri":A + B/ri**2,"sigma_r_ro":A - B/ro**2,"sigma_t_ro":A + B/ro**2}

def solve_buckling_euler(inputs):
  E=to_si(inputs.get("material",{}).get("E")); I=to_si(inputs.get("geometry",{}).get("I")); L=to_si(inputs.get("geometry",{}).get("L")); K=to_si(inputs.get("geometry",{}).get("K"),1.0)
  if None in (E,I,L): return {}
  return {"P_cr": (math.pi**2)*E*I/((K*L)**2)}
def solve_buckling_johnson(inputs):
  Sy=to_si(inputs.get("material",{}).get("S_y")); E=to_si(inputs.get("material",{}).get("E")); A=to_si(inputs.get("geometry",{}).get("A")); I=to_si(inputs.get("geometry",{}).get("I"))
  L=to_si(inputs.get("geometry",{}).get("L")); K=to_si(inputs.get("geometry",{}).get("K"),1.0)
  if None in (Sy,E,A,I,L): return {}
  r=(I/A)**0.5; P=A*Sy*(1.0 - (Sy/(2.0*math.pi**2*E))*((K*L/r)**2)); return {"P_cr_johnson":P,"slenderness":(K*L)/r}

def solve_torsion_solid(inputs):
  T=to_si(inputs.get("loads",{}).get("T")); L=to_si(inputs.get("geometry",{}).get("L"))
  G=to_si(inputs.get("material",{}).get("G")); d=to_si(inputs.get("geometry",{}).get("d"))
  if None in (T,L,G,d): return {}
  J=math.pi*d**4/32.0; tau=16*T/(math.pi*d**3); theta=T*L/(G*J); return {"tau_max":tau,"theta":theta,"J":J}
def solve_torsion_hollow(inputs):
  T=to_si(inputs.get("loads",{}).get("T")); L=to_si(inputs.get("geometry",{}).get("L"))
  G=to_si(inputs.get("material",{}).get("G")); do=to_si(inputs.get("geometry",{}).get("do")); di=to_si(inputs.get("geometry",{}).get("di"))
  if None in (T,L,G,do,di): return {}
  J=math.pi*(do**4 - di**4)/32.0; tau=16*T/(math.pi*do**3*(1-(di/do)**4)); theta=T*L/(G*J); return {"tau_max":tau,"theta":theta,"J":J}

def solve_spring_helical(inputs):
  d=to_si(inputs.get("geometry",{}).get("d")); D=to_si(inputs.get("geometry",{}).get("D"))
  na=to_si(inputs.get("geometry",{}).get("n_a")); G=to_si(inputs.get("material",{}).get("G")); F=to_si(inputs.get("loads",{}).get("F"))
  if None in (d,D,na,G,F): return {}
  k=(G*d**4)/(8*na*D**3); delta=F/k; C=D/d; Ks=((4*C-1)/(4*C-4)) + 0.615/C; tau=Ks*(8*F*D)/(math.pi*d**3)
  return {"k":k,"deflection":delta,"tau_max":tau,"Wahl_factor":Ks}

def solve_bearing_L10(inputs):
  C=to_si(inputs.get("catalog",{}).get("C")); P=to_si(inputs.get("loads",{}).get("P")); rpm=to_si(inputs.get("operating",{}).get("rpm"))
  if None in (C,P,rpm): return {}
  L10_rev=((C/P)**3)*1e6; L10_hours=L10_rev/(60.0*rpm); return {"L10_rev":L10_rev,"L10_hours":L10_hours}

def solve_bolt_preload(inputs):
  At=to_si(inputs.get("geometry",{}).get("A_t")); Sp=to_si(inputs.get("material",{}).get("S_p")); n=inputs.get("geometry",{}).get("n") or 1
  Fext=to_si(inputs.get("loads",{}).get("F_external"),0.0)
  if None in (At,Sp): return {}
  Fpre=0.75*At*Sp; sigma=Fpre/At; reserve=n*Fpre - Fext; return {"F_pre_per_bolt":Fpre,"sigma_at_preload":sigma,"joint_clamp_reserve":reserve}

def solve_weld_fillet_linear(inputs):
  t=to_si(inputs.get("geometry",{}).get("t")); Lw=to_si(inputs.get("geometry",{}).get("Lw")); F=to_si(inputs.get("loads",{}).get("F"))
  if None in (t,Lw,F): return {}
  Aw=t*Lw; tau=F/Aw; return {"tau":tau}

def solve_power_screw(inputs):
  F=to_si(inputs.get("loads",{}).get("F")); dm=to_si(inputs.get("geometry",{}).get("d_m")); lead=to_si(inputs.get("geometry",{}).get("lead"))
  mu=inputs.get("tribology",{}).get("mu") or 0.15; mu_c=inputs.get("tribology",{}).get("mu_collar",0.0); d_c=to_si(inputs.get("geometry",{}).get("d_collar",{})) or 0.0
  if None in (F,dm,lead): return {}
  alpha=math.atan(lead/(math.pi*dm)); phi=math.atan(mu); T_thread=F*dm/2.0*math.tan(alpha+phi); T_collar=F*mu_c*d_c/2.0
  eta=math.tan(alpha)/(math.tan(alpha)+mu); return {"T_total":T_thread+T_collar,"T_thread":T_thread,"T_collar":T_collar,"efficiency_est":eta}

def solve_disc_brake_uniform_wear(inputs):
  F=to_si(inputs.get("loads",{}).get("F")); mu=inputs.get("tribology",{}).get("mu") or 0.35; ri=to_si(inputs.get("geometry",{}).get("r_i")); ro=to_si(inputs.get("geometry",{}).get("r_o"))
  if None in (F,ri,ro): return {}
  return {"T": mu*F*((ro+ri)/2.0)}

def solve_press_fit(inputs):
  rs=to_si(inputs.get("shaft",{}).get("r_s")); Es=to_si(inputs.get("shaft",{}).get("E")); nus=to_si(inputs.get("shaft",{}).get("nu"),0.3)
  ri=to_si(inputs.get("hub",{}).get("r_i")); ro=to_si(inputs.get("hub",{}).get("r_o")); Eh=to_si(inputs.get("hub",{}).get("E")); nuh=to_si(inputs.get("hub",{}).get("nu"),0.3)
  delta=to_si(inputs.get("fit",{}).get("delta")); 
  if None in (rs,Es,ri,ro,Eh,delta): return {}
  Cs=(1/Es)*((1-nus**2)/rs); Ch=(1/Eh)*(((1 - nuh**2)*(ro**2 + ri**2))/((ro**2 - ri**2)*ri)); p=delta/(Cs+Ch); return {"contact_pressure":p}

REGISTRY = {
  "beam.eb.simply_supported.udl": solve_beam_udl,
  "pv.cylinder.thin": solve_pv_thin,
  "pv.cylinder.thick": solve_pv_thick,
  "column.euler": solve_buckling_euler,
  "column.johnson": solve_buckling_johnson,
  "shaft.torsion.solid": solve_torsion_solid,
  "shaft.torsion.hollow": solve_torsion_hollow,
  "spring.helical.compression": solve_spring_helical,
  "bearing.ball.L10": solve_bearing_L10,
  "bolt.preload_proof": solve_bolt_preload,
  "weld.fillet.linear": solve_weld_fillet_linear,
  "power.screw": solve_power_screw,
  "brake.disk.uniform_wear": solve_disc_brake_uniform_wear,
  "fit.press.interference": solve_press_fit,
}

# ================= Streamlit UI =================
st.title("🛠️ Shigley MegaPack — Parse ✚ Solve")
st.caption("Industrial-grade single file • English problem parsing • Engineering-unit outputs")

tab_parse, tab_manual, tab_docs = st.tabs(["Parse from text", "Manual solver", "Docs & Examples"])

with tab_parse:
  example = ("A simply supported steel beam of span 2 m with a rectangular section 40 mm by 60 mm. "
             "The beam carries a uniformly distributed load of 5 kN/m over the span. "
             "Take E = 210 GPa. Determine the midspan deflection and the maximum bending stress.")
  txt = st.text_area("Problem text", example, height=220)
  if st.button("Parse & Solve"):
    spec = build_spec(txt)
    st.subheader("Detected"); st.write(f"**Class:** `{spec['class']}`  |  **Confidence:** `{spec['confidence']}`")
    c1,c2 = st.columns(2)
    with c1: st.markdown("**Inputs**"); st.json(spec.get("inputs", {}), expanded=False)
    with c2: st.markdown("**Assumptions / Ambiguities**"); st.json({"assumptions":spec.get("assumptions",[]),"ambiguities":spec.get("ambiguities",[])}, expanded=False)
    cls = spec["class"]
    fn = REGISTRY.get(cls)
    if not fn and cls=="pv.cylinder.thin": fn = REGISTRY["pv.cylinder.thin"]
    st.subheader("Results")
    if fn:
      out_si = fn(spec if cls.startswith("beam") or cls.startswith("pv.cylinder.thin") else spec.get("inputs",{}))
      if not out_si: st.warning("Insufficient inputs. Use Manual tab to provide missing fields."); 
      else:
        rows=[]
        for k,v in out_si.items():
          pref = pick_unit_pref(k); val,lab = fmt_eng(v,pref) if pref else (v,"(SI)")
          rows.append((k,val,lab,v))
        st.table(rows)
        st.download_button("Download results (JSON, SI)", data=json.dumps(out_si, indent=2), file_name="results_si.json", mime="application/json")
    else:
      st.info("No solver mapped. Switch to Manual.")

with tab_manual:
  st.markdown("Pick a class & paste inputs JSON (SI).")
  cls = st.selectbox("Class", sorted(REGISTRY.keys()), index=0)
  default_inputs = {
    "geometry":{"L":{"si":2.0},"section":{"b":{"si":0.04},"h":{"si":0.06}}},
    "material":{"E":{"si":2.1e11}},
    "loads":[{"type":"uniform","q":{"si":5000.0}}]
  }
  raw = st.text_area("Inputs JSON (editable)", json.dumps(default_inputs, indent=2), height=260)
  if st.button("Solve (manual)"):
    try:
      inputs = json.loads(raw)
      if cls == "beam.eb.simply_supported.udl":
        spec = {"class":cls, "inputs": inputs}; out_si = REGISTRY[cls](spec)
      elif cls.startswith("pv.cylinder"):
        out_si = REGISTRY[cls]({"inputs":inputs}) if cls=="pv.cylinder.thin" else REGISTRY[cls](inputs)
      else:
        out_si = REGISTRY[cls](inputs)
      if not out_si: st.warning("Solver returned empty (missing inputs?).")
      else:
        rows=[]
        for k,v in out_si.items():
          pref=pick_unit_pref(k); val,lab=(v,"(SI)") if not pref else fmt_eng(v,pref)
          rows.append((k,val,lab,v))
        st.subheader("Results"); st.table(rows)
        st.download_button("Download results (JSON, SI)", data=json.dumps(out_si, indent=2), file_name="results_si.json", mime="application/json")
    except Exception as e:
      st.error(str(e))

with tab_docs:
  st.markdown("""
### What’s inside
- **Parser** for archetypes: beam UDL, thin-walled cylinder, Euler buckling (extensible).
- **Solvers** bundled in one file: beams, PV thin/thick, buckling (Euler/Johnson), torsion (solid/hollow), helical spring, bearing L10, bolt preload, weld fillet, power screw, disk brake (uniform wear), press fit.
- **Engineering units** on display (MPa, kN, mm, …) + SI JSON download.
- **Notes**: For standards (AGMA/ISO), supply factors as inputs (factor computation from tables is out of scope in this single file).
  """)
  st.divider()
  st.markdown("#### Example inputs")
  examples = {
    "Beam UDL": {
      "geometry": {"L":{"si":2.0}, "section":{"b":{"si":0.04},"h":{"si":0.06}}},
      "material": {"E":{"si":2.1e11}},
      "loads": [{"type":"uniform","q":{"si":5000.0}}]
    },
    "Thin cylinder": {
      "geometry": {"R":{"si":0.5},"t":{"si":0.006}},
      "loads": [{"type":"pressure","p":{"si":2e6}}]
    },
    "Bearing L10": {
      "catalog": {"C":{"si":20000.0}},
      "loads": {"P":{"si":5000.0}},
      "operating": {"rpm":{"si":1800.0}}
    },
    "Spring helical": {
      "geometry": {"d":{"si":0.006},"D":{"si":0.06},"n_a":{"si":8}},
      "material": {"G":{"si":79e9}},
      "loads": {"F":{"si":500.0}}
    }
  }
  pick = st.selectbox("Pick example", list(examples.keys()))
  st.code(json.dumps(examples[pick], indent=2), language="json")
