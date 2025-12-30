
import json, argparse, random, math

def select_per_topic(harvest, per_topic=15, seed=123):
    random.seed(seed)
    by_topic = {}
    for rec in harvest:
        t = rec.get("topic","unknown")
        by_topic.setdefault(t, []).append(rec)
    selected=[]
    for t, items in by_topic.items():
        random.shuffle(items)
        selected.extend(items[:per_topic])
    return selected

def main():
    ap = argparse.ArgumentParser(description="Build per-topic dataset from harvest results.")
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--per-topic", dest="per_topic", type=int, default=15)
    ap.add_argument("--out", dest="outfile", required=True)
    args = ap.parse_args()
    data = json.load(open(args.infile,"r",encoding="utf-8"))
    selected = select_per_topic(data, per_topic=args.per_topic)
    with open(args.out,"w",encoding="utf-8") as f:
        json.dump(selected, f, indent=2)
    print(f"Wrote {len(selected)} items (<= {args.per_topic} per topic) → {args.out}")

if __name__ == "__main__":
    main()
