
#!/usr/bin/env python3

"""
shigley_lexicon_builder.py — Industrial lexicon extractor for mechanical design PDFs.
Usage:
  python shigley_lexicon_builder.py <PDF> <OUT_DIR> [--min-count 1] [--target 80000]

Outputs:
  - wordlist_unique.txt
  - wordfreq.csv
  - bigrams.csv / trigrams.csv
  - dictionary_entries.csv (unigrams + frequent n-grams up to target size)
  - stats.json

Requires: PyPDF2, pdfminer.six
"""
import argparse, re, collections, csv, json, sys, time
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z\-’']+")

def extract_text_pypdf2(pdf_path:Path)->str:
    import PyPDF2
    text=""
    with open(pdf_path,"rb") as f:
        reader=PyPDF2.PdfReader(f)
        for page in reader.pages:
            try: text+=page.extract_text() or ""+"\n"
            except Exception: continue
    return text

def extract_text_pdfminer(pdf_path:Path)->str:
    from pdfminer.high_level import extract_text
    return extract_text(str(pdf_path))

def tokens_from_text(text:str):
    return [tok.lower() for tok in TOKEN_RE.findall(text) if len(tok)>=2]

def write_csv(path, header, rows):
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f); w.writerow(header); w.writerows(rows)

def build_dictionary(freq, bigrams, trigrams, target_size=80000):
    entries=[]
    for w,c in freq.most_common(): entries.append(("unigram",w,c))
    for (a,b),c in bigrams.most_common():
        if len(entries)>=target_size: break
        entries.append(("bigram",f"{a} {b}",c))
    for (a,b,c_),n in trigrams.most_common():
        if len(entries)>=target_size: break
        entries.append(("trigram",f"{a} {b} {c_}",n))
    return entries[:target_size]

def main():
    ap=argparse.ArgumentParser(description="Build PDF lexicon")
    ap.add_argument("pdf",type=Path)
    ap.add_argument("out",type=Path)
    ap.add_argument("--min-count",type=int,default=1)
    ap.add_argument("--target",type=int,default=80000)
    args=ap.parse_args()

    start=time.time()
    text=""
    try: text=extract_text_pypdf2(args.pdf)
    except Exception as e: print("[WARN] PyPDF2 failed:",e,file=sys.stderr)
    if len(text)<1000:
        try: text=extract_text_pdfminer(args.pdf)
        except Exception as e:
            print("[ERROR] pdfminer also failed:",e,file=sys.stderr); sys.exit(1)

    tokens=tokens_from_text(text)
    freq=collections.Counter(tokens)
    if args.min_count>1: freq=collections.Counter({w:c for w,c in freq.items() if c>=args.min_count})

    words=[w for w in tokens if len(w)>=2]
    bigrams=collections.Counter(zip(words,words[1:]))
    trigrams=collections.Counter(zip(words,words[1:],words[2:]))

    args.out.mkdir(parents=True,exist_ok=True)
    write_csv(args.out/"wordfreq.csv",["word","count"],freq.most_common())
    write_csv(args.out/"bigrams.csv",["bigram","count"],[(f"{a} {b}",c) for (a,b),c in bigrams.most_common()])
    write_csv(args.out/"trigrams.csv",["trigram","count"],[(f"{a} {b} {c_}",n) for (a,b,c_),n in trigrams.most_common()])
    (args.out/"wordlist_unique.txt").write_text("\n".join(sorted(freq)),encoding="utf-8")

    dict_entries=build_dictionary(freq,bigrams,trigrams,args.target)
    write_csv(args.out/"dictionary_entries.csv",["type","token","count"],dict_entries)

    stats={"unique":len(freq),"tokens":len(tokens),
           "bigrams":len(bigrams),"trigrams":len(trigrams),
           "dict_size":len(dict_entries),"elapsed_sec":time.time()-start}
    (args.out/"stats.json").write_text(json.dumps(stats,indent=2),encoding="utf-8")
    print("Done:",json.dumps(stats))

if __name__=="__main__":
    main()
