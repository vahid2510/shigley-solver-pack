# app_streamlit_solver.py — UI with parsing + solving
import json
import streamlit as st
from builder_core import build_spec
from solver_core import solve

st.set_page_config(page_title="Mechanical Problem Parser + Solver", page_icon="🛠️", layout="wide")

st.title("🛠️ Mechanical Problem Parser + Solver (Phase‑1)")
st.caption("Paste an English textbook-style problem. I’ll classify & extract, then compute key results.")

example = ("A simply supported steel beam of span 2 m with a rectangular section 40 mm by 60 mm. "
           "The beam carries a uniformly distributed load of 5 kN/m over the entire span. "
           "Take E = 210 GPa, nu = 0.3. Determine the midspan deflection and the maximum bending stress.")

txt = st.text_area("Problem text", example, height=220)
colA, colB = st.columns(2)
with colA:
    parse = st.button("Parse problem")
with colB:
    solve_btn = st.button("Solve")

spec = None
if parse and txt.strip():
    spec = build_spec(txt)
    st.session_state["last_spec"] = spec
if solve_btn:
    if "last_spec" not in st.session_state and txt.strip():
        st.session_state["last_spec"] = build_spec(txt)
    spec = st.session_state.get("last_spec")

if spec:
    st.subheader("Detected class and confidence")
    st.write(f"**Class:** `{spec['class']}`   |   **Confidence:** `{spec['confidence']}`")

    st.subheader("Inputs (JSON)")
    st.json(spec.get("inputs", {}), expanded=False)

    st.subheader("Outputs requested")
    st.json(spec.get("outputs", []), expanded=False)

    st.subheader("Assumptions & Ambiguities")
    c1, c2 = st.columns(2)
    with c1: st.json(spec.get("assumptions", []), expanded=False)
    with c2: st.json(spec.get("ambiguities", []), expanded=False)

    res = solve(spec) if solve_btn else {}
    if res:
        st.subheader("Solver results (SI units)")
        st.json(res, expanded=False)

    st.subheader("Raw ProblemSpec JSON")
    st.code(json.dumps(spec, indent=2), language="json")
else:
    st.info("Click **Parse problem** then **Solve**.", icon="ℹ️")