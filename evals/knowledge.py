#!/usr/bin/env python3
"""Benchmark the SHIPPED knowledge layer (what users get) on the same 30 questions as retrieval.py.

  on-topic@8   share of the top 8 whose entry text contains an expected term
  hit@8        questions with >= 3 on-topic entries in the top 8
  book@8       questions whose top 8 include a book/playbook page
  source@8     share of the top 8 whose POINTED ORIGINAL (the page or the ~90 s of video it links to) contains an
               expected term: do the citations lead somewhere relevant? Needs the owner's private index.

  evals/knowledge.py [--mode keyword|hybrid]
"""
import argparse, json, pathlib, re, sqlite3, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "skills/hormozi/scripts/hormozi.py"
Qs = [json.loads(l) for l in open(ROOT / "evals/questions.jsonl")]
priv = sqlite3.connect(ROOT / "index/hormozi.db") if (ROOT / "index/hormozi.db").exists() else None
PAGED = ROOT / "sources/books/paged"

ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="keyword", choices=["keyword", "hybrid"]); a = ap.parse_args()
py = str(ROOT / "skills/hormozi/.venv/bin/python") if a.mode == "hybrid" else sys.executable
env = {"HORMOZI_NO_VENV": "1"} if a.mode == "keyword" else {}

def hits(q):
    import os
    out = subprocess.run([py, str(CLI), "search", q, "-n", "8", "--mode", a.mode], capture_output=True, text=True, env={**os.environ, **env}).stdout
    return re.findall(r"^\[([^\]]+)\] (.*)$", out, re.M)

def entry(db, i):
    return json.loads(db.execute("SELECT json FROM doc WHERE id=?", (i,)).fetchone()[0])

def original(o):
    if o.get("src") == "book":
        slug = next((p.stem for p in PAGED.glob("*.md") if o["book"].lower().replace("$100m ", "").replace(" — ", " ").split()[0] in p.stem.lower()), None)
        name = {"$100M Offers": "100M-Offers", "$100M Leads": "100M-Leads", "$100M Money Models": "100M-Money-Models"}.get(o["book"], slug)
        f = PAGED / f"{name}.md"
        if not f.exists():
            f = next((p for p in PAGED.glob("*.md") if re.sub(r"[^a-z]", "", p.stem.lower()) == re.sub(r"[^a-z]", "", o["book"].lower().replace("$", ""))), None)
        if not f: return ""
        m = re.search(rf"=== p\. {o['page']} ===\n(.*?)(?=\n=== p\. |\Z)", f.read_text(), re.S); return m.group(1) if m else ""
    if not priv: return ""
    r = priv.execute("SELECT body FROM meta WHERE url LIKE ? AND title LIKE ?", (f"%v={o['video']}%", f"% @ {o['at']}")).fetchone()
    return r[0] if r else ""

sys.path.insert(0, str(CLI.parent))
import os; subprocess.run([sys.executable, str(CLI), "stats"], capture_output=True, env={**os.environ, "HORMOZI_NO_VENV": "1"})  # (re)build the index first
dbp = max((ROOT / "skills/hormozi/.cache").glob("knowledge-*.db"), key=lambda p: p.stat().st_mtime)
kdb = sqlite3.connect(dbp)
tot = {"on": 0, "src": 0, "srcn": 0, "hit": 0, "book": 0, "n": 0}
for Q in Qs:
    hs = hits(Q["q"]); on = 0; bk = False
    for i, head in hs:
        o = entry(kdb, i); txt = (head + " " + json.dumps(o, ensure_ascii=False)).lower()
        good = any(e in txt for e in Q["expect"]); on += good; bk |= o.get("src") == "book"
        orig = original(o) if "at" in o or "page" in o else ""
        if orig: tot["srcn"] += 1; tot["src"] += any(e in orig.lower() for e in Q["expect"])
    tot["on"] += on / 8; tot["hit"] += on >= 3; tot["book"] += bk; tot["n"] += 1
n = tot["n"]
print(f"shipped layer ({a.mode}): on-topic@8 {tot['on']/n:.0%}  hit@8 {tot['hit']}/{n}  book@8 {tot['book']}/{n}  "
      f"source@8 {tot['src']/max(1,tot['srcn']):.0%} of {tot['srcn']} pointed originals")
