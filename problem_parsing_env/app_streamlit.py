# app_streamlit.py — Paste a problem, get a structured breakdown
import json
import streamlit as st
from builder_core import build_spec

st.set_page_config(page_title="Mechanical Problem Parser", page_icon="🛠️", layout="wide")

st.title("🛠️ Mechanical Problem Parser (Phase‑1)")
st.caption("Paste an English textbook-style problem. I’ll classify it and extract inputs/outputs.")

example = ("A simply supported steel beam of span 2 m with a rectangular section 40 mm by 60 mm. "
           "The beam carries a uniformly distributed load of 5 kN/m over the entire span. "
           "Take E = 210 GPa, nu = 0.3. Determine the midspan deflection and the maximum bending stress.")

txt = st.text_area("Problem text", example, height=220)
run = st.button("Parse problem")

if run and txt.strip():
    spec = build_spec(txt)
    st.subheader("Detected class and confidence")
    st.write(f"**Class:** `{spec['class']}`   |   **Confidence:** `{spec['confidence']}`")

    st.subheader("Inputs (flattened)")
    def flatten(d, prefix=""):
        rows=[]
        if isinstance(d, dict):
            for k,v in d.items():
                rows+=flatten(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(d, list):
            for i,v in enumerate(d):
                rows+=flatten(v, f"{prefix}[{i}]")
        else:
            rows.append((prefix, d))
        return rows

    st.table(flatten(spec.get("inputs", {})))

    st.subheader("Outputs requested")
    st.json(spec.get("outputs", []), expanded=False)

    st.subheader("Assumptions & Ambiguities")
    c1, c2 = st.columns(2)
    with c1: st.json(spec.get("assumptions", []), expanded=False)
    with c2: st.json(spec.get("ambiguities", []), expanded=False)

    st.subheader("Raw JSON")
    st.code(json.dumps(spec, indent=2), language="json")
else:
    st.info("Click **Parse problem** to run.", icon="ℹ️")