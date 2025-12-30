# parse_cli.py — quick CLI wrapper
import argparse, json, sys
from builder_core import build_spec

ap = argparse.ArgumentParser(description="CLI problem parser")
ap.add_argument("--text", type=str, required=True, help="Raw problem text")
ap.add_argument("--out", type=str, default="", help="Optional JSON output path")
args = ap.parse_args()

spec = build_spec(args.text)

if args.out:
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {args.out}")
else:
    print(json.dumps(spec, indent=2))