# tests/test_problem_builder.py
# Minimal smoke test: ensure builder runs and emits required keys
import json, subprocess, sys, os, pathlib
root = pathlib.Path(__file__).resolve().parents[1]
builder = root / "tools" / "problem_spec_builder_v2.py"
samples = (root / "samples" / "problems").glob("*.txt")
outdir = root / "outputs"
outdir.mkdir(exist_ok=True)

required_keys = {"class","confidence","inputs","outputs"}

rc=0
for s in samples:
    out = outdir / (s.stem + "_spec.json")
    cmd = [sys.executable, str(builder), "--in", str(s), "--out", str(out)]
    try:
        subprocess.check_call(cmd)
        data = json.loads(out.read_text(encoding="utf-8"))
        missing = required_keys - set(data.keys())
        if missing:
            print(f"[FAIL] {s.name}: missing {missing}")
            rc=1
        else:
            print(f"[OK] {s.name}: class={data['class']} conf={data['confidence']}")
    except Exception as e:
        print(f"[ERROR] {s.name}: {e}")
        rc=1

sys.exit(rc)