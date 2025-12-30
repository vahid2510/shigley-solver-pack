
import re, json, argparse, sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Try both backends
def extract_text_pypdf2(path: str) -> List[str]:
    try:
        import PyPDF2
    except Exception as e:
        raise RuntimeError("PyPDF2 not installed") from e
    pages=[]
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i in range(len(reader.pages)):
            pages.append(reader.pages[i].extract_text() or "")
    return pages

def extract_text_pdfminer(path: str) -> List[str]:
    try:
        from pdfminer.high_level import extract_text
    except Exception as e:
        raise RuntimeError("pdfminer.six not installed") from e
    # pdfminer extracts whole doc; split crudely on '\f' page breaks if present
    txt = extract_text(path)
    return txt.split("\f")

def load_topics_yaml(path: str) -> Dict[str, Any]:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def first_n_words(s: str, n: int = 25) -> str:
    words = re.findall(r"\S+", s)
    return " ".join(words[:n])

def detect_problem_blocks(page_text: str) -> List[str]:
    # Heuristic: find lines starting with a number or "Problem" patterns until next blank line
    blocks = []
    lines = page_text.splitlines()
    buf=[]; active=False
    for ln in lines:
        if re.match(r"^\s*(Problem\s*\d+\.|PROBLEM\s*\d+\.|\d{1,3}\.\s)", ln):
            if buf:
                blocks.append("\n".join(buf).strip())
                buf=[]
            active=True
            buf.append(ln)
        elif active:
            # continue current block until a clear separator
            if ln.strip()=="" and buf:
                blocks.append("\n".join(buf).strip())
                buf=[]; active=False
            else:
                buf.append(ln)
    if buf: blocks.append("\n".join(buf).strip())
    return blocks

def guess_topic(text: str, topics: Dict[str, Any]) -> (str, str):
    t_best="unknown"; solver=None; score=0
    low = text.lower()
    for t, cfg in topics.items():
        kws = cfg.get("keywords", [])
        sc = sum(1 for kw in kws if kw.lower() in low)
        if sc>score:
            score=sc; t_best=t; solver=cfg.get("solver")
    return t_best, (solver or "unknown")

def harvest(pdf_path: str, topics_path: str) -> List[Dict[str, Any]]:
    # pick backend
    pages=None
    try:
        pages = extract_text_pypdf2(pdf_path)
    except Exception:
        pages = None
    if not pages:
        try:
            pages = extract_text_pdfminer(pdf_path)
        except Exception as e:
            raise RuntimeError("No PDF backend succeeded. Install PyPDF2 or pdfminer.six.") from e

    topics = load_topics_yaml(topics_path)
    results=[]
    for pno, ptxt in enumerate(pages, start=1):
        if not ptxt: continue
        # quick chapter guess
        chap_match = re.search(r"^\s*Chapter\s+(\d+)", ptxt, re.I|re.M)
        chapter = chap_match.group(1) if chap_match else None
        # find problem blocks
        blocks = detect_problem_blocks(ptxt)
        for blk in blocks:
            # problem no
            mno = re.search(r"(?:Problem\s*)?(\d{1,3})\.", blk, re.I)
            pnum = mno.group(1) if mno else None
            # 25-word excerpt
            excerpt = first_n_words(re.sub(r"\s+", " ", blk), 25)
            topic, solver = guess_topic(blk, topics)
            results.append({
                "page": pno,
                "chapter_guess": chapter,
                "problem_no": pnum,
                "excerpt_25w": excerpt,
                "topic": topic,
                "solver_class_guess": solver
            })
    return results

def main():
    ap = argparse.ArgumentParser(description="Harvest Shigley problems with page citations (copyright-safe).")
    ap.add_argument("--pdf", required=True, help="Path to your Shigley PDF")
    ap.add_argument("--topics", default="topics.yaml", help="Path to topics.yaml")
    ap.add_argument("--out", required=True, help="Output JSON")
    args = ap.parse_args()
    data = harvest(args.pdf, args.topics)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Harvested {len(data)} problem-like blocks → {args.out}")

if __name__ == "__main__":
    main()
