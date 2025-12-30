# solve_cli.py — Parse + Solve end-to-end from raw text
import argparse, json
from builder_core import build_spec
from solver_core import solve

ap = argparse.ArgumentParser(description="Parse and solve a mechanical problem (Phase‑1)")
ap.add_argument("--text", type=str, required=True, help="Raw problem text")
ap.add_argument("--out", type=str, default="", help="Optional JSON output path for ProblemSpec")
args = ap.parse_args()

spec = build_spec(args.text)
res = solve(spec)
print("# ProblemSpec")
print(json.dumps(spec, indent=2))
print("\n# Solver results (SI)")
print(json.dumps(res, indent=2))

if args.out:
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)