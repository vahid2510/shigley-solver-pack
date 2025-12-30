
import json, argparse, sys
from solvers.registry import REGISTRY
ap = argparse.ArgumentParser(description="Shigley Solver Pack — solve by class key")
ap.add_argument("--class", dest="cls", required=True); ap.add_argument("--in-json", dest="in_json", required=True)
args = ap.parse_args()
if args.cls not in REGISTRY:
    print("Unknown class:", args.cls, "\nAvailable:", ", ".join(sorted(REGISTRY.keys()))); sys.exit(1)
inputs = json.load(open(args.in_json,"r",encoding="utf-8"))
out = REGISTRY[args.cls](inputs); print(json.dumps(out, indent=2))
