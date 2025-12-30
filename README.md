# Shigley-NLU Solver Framework

The Shigley-NLU bundle turns short, textbook-style descriptions into fully
specified mechanical design problems and routes them to a library of analytical
solvers.  It grew out of experiments on *Shigley's Mechanical Engineering
Design* problems, but the pipeline is generic enough for any problem phrased in
natural language.

---

## Why it exists

1. **Understand the prompt** – recognise the mechanical scenario (beam, shaft,
   bearing, pressure vessel, …) and extract the governing dimensions, loads,
   materials, and requested outputs.
2. **Normalise the data** – convert units to SI, fill in derived quantities, and
   validate dimensional consistency.
3. **Solve and explain** – pick the right analytical solver, run it, and report
   every value with traceable inputs.

Each stage is modular so you can embed your own parser, bring a different solver
library, or plug our solver set into your own UI.

---

## Architecture Overview

| Module | Purpose |
|--------|---------|
| `problem_parsing_env/builder_core.py` | Rule-based spec builder that maps free-form text to the structured schema. |
| `problem_parsing_env/solver_core.py` | Bridge that finds the solver class, prepares data, and post-processes results. |
| `solvers/` | Stand-alone analytical solvers (beams, shafts, springs, bearings, fatigue, etc.) registered in `registry.py`. |
| `ui/app_manual_solver.py` | Streamlit workspace for manual entry or parser-assisted solving. |
| `tools/problem_spec_builder_v2.py` | CLI helper that converts text samples into JSON specs. |
| `tests/` | Unit and smoke tests for parsers and solver contracts. |

Support files under `data/` provide reference tables (e.g., notch factors) that
some solvers rely on.

---

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The root `requirements.txt` covers both the solver stack and the optional
parsing environment.  If you keep `problem_parsing_env` in a separate virtual
environment, copy the same requirements there.

---

## Usage

### 1. Parse a natural-language problem (optional)

```powershell
python problem_parsing_env\solve_cli.py --text "A simply supported steel beam of span 2 m carries a uniform load of 5 kN/m. E = 210 GPa. Find the midspan deflection."
```

The CLI prints the structured spec, solver choice, and computed outputs.  When
using the Streamlit interface (`streamlit run ui/app_manual_solver.py`) you can
paste similar text into the *Auto Parse* tab.

### 2. Run a solver directly

```powershell
python solve_any.py --class beam.eb.simply_supported.udl --in-json examples\beam_udl.json
```

This bypasses the parser and feeds a hand-crafted or auto-generated JSON spec to
the requested solver.

### 3. Launch the Streamlit workspace

```powershell
streamlit run ui/app_manual_solver.py
```

The UI exposes both manual form entry and natural-language parsing.  It loads
the optional parser automatically when `problem_parsing_env` is present.

---

## Supported Solver Classes

The registry currently includes the following class keys (see
`solvers/registry.py` for the authoritative list):

- `beam.eb.simply_supported.udl`, `beam.eb.simply_supported.point_mid`, `beam.cantilever.point_end`
- `shaft.torsion.solid`, `shaft.torsion.hollow`, `shaft.analysis.segmented`
- `shaft.design.d_required_static`, `shaft.design.d_required_fatigue`
- `failure.von_mises`, `failure.tresca`
- `fatigue.endurance_modified`, `fatigue.goodman`, `fatigue.gerber`, `fatigue.soderberg`
- `spring.helical.compression`, `spring.helical.extension`, `spring.helical.torsion`, `spring.helical.parallel`
- `bearing.ball.L10`, `bearing.ball.life_reliability`, `bearing.ball.required_C`, `bearing.ball.equivalent_load`
- `bolt.preload_proof`, `weld.fillet.linear`
- `gear.spur.agma_bending_basic`, `gear.spur.agma_contact_basic`
- `pv.cylinder.thin`, `pv.cylinder.thick`
- `clutch.single_disc.uniform_pressure`, `clutch.single_disc.uniform_wear`
- `belt.flat.power`, `belt.flat.tension_ratio`
- `column.euler`, `column.johnson`
- `power.screw.raise`

Adding a new solver is as simple as implementing a function under `solvers/` and
registering it in `solvers/registry.py`.  Keep the input contract JSON friendly
and add a smoke test in `tests/` to lock in the behaviour.

---

## Structured Spec Schema

Specs are JSON documents with the following top-level keys:

```jsonc
{
  "class": "beam.eb.simply_supported.udl",
  "inputs": {
    "geometry": {"L": {"si": 2.0}},
    "loads": [{"type": "uniform", "q": {"si": 5000.0}}],
    "material": {"E": {"si": 2.1e11}}
  },
  "outputs": ["delta_mid", "M_max"],
  "metadata": {...}            // optional extras such as page references
}
```

Every solver consumes a subset of these nested dictionaries.  The helper
`solvers.common.to_si` accepts plain floats (`5000.0`) or dictionaries with
`value`, `unit`, and `si` keys, so feel free to annotate units when convenient.

---

## Testing

Run all tests with:

```powershell
python -m pytest
```

The suite includes parser-driven scenarios and solver smoke coverage.  When you
add a new solver, extend `tests/test_solver_registry.py` (or create a dedicated
test module) with representative inputs and assertions.

---

## Localisation

While the test data is in English, the UI is built with bilingual support in
mind.  The parser currently focuses on English phrasing, but the architecture
allows adding alternative tokenisers or lexicons for other languages.

---

## License
MIT LICENSE 
