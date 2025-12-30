# Problem Parsing + Solver Environment

## Install (UI)
```powershell
pip install streamlit
```
(If you plan to use the lexicon builder, also install `PyPDF2` and `pdfminer.six` in your other bundle.)

## Run the UI (Parse + Solve)
```powershell
streamlit run app_streamlit_solver.py
```

## CLI quick test
```powershell
python solve_cli.py --text "A simply supported steel beam of span 2 m with a rectangular section 40 mm by 60 mm. The beam carries a uniformly distributed load of 5 kN/m. Take E=210 GPa, nu=0.3. Determine the midspan deflection and the maximum bending stress."
```

### Notes on solvers
- **Beam (EB, simply supported, UDL over full span)**  
  δ_mid = 5 q L⁴ / (384 E I), σ_max = M_max c / I with M_max = q L² / 8, c = h/2.  
  If I is missing but b,h are present, I = b h³ / 12.
- **Thin-walled cylinder (internal pressure)**  
  σ_hoop = p R / t, σ_long = p R / (2 t). If σ_y is provided, FOS = σ_y / max(σ_hoop, σ_long).
- **Euler buckling**  
  P_cr = π² E I / (K L)².
- **SDOF base-excited harmonic**  
  Reports fn and T. If m,k,ζ,a0,f exist, computes **relative** displacement amplitude:  
  X_rel = (a0/ω²) · [ r² / √((1−r²)² + (2ζr)²) ], with r = ω/ω_n.

All results are returned in SI units. You can scale/format as needed in your frontend.


cd problem_parsing_env
streamlit run app_streamlit_solver.py