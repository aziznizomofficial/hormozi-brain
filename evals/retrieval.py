#!/usr/bin/env python3
"""Retrieval benchmark: does the top-8 contain on-topic, authoritative material?

Systems compared (same questions, same scorer):
  ours          hybrid search over the whole library
  ours-keyword  keyword-only over the whole library
  moremozi-only the corpus the strongest public repos ship (viclaranja/hormozi-ai-skill, poseljacob/ask-hormozi)
  notes-only    third-party course notes (the corpus of the markdown-knowledge-base repos)

Metrics per system:
  on-topic@8    share of the top 8 whose text contains an expected term
  hit@8         questions where at least 3 of the top 8 are on-topic
  book@8        questions where the top 8 includes a book/playbook page (citable canonical source)
"""
import json, re, sqlite3, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
db = sqlite3.connect(ROOT / "index/hormozi.db")
Qs = [json.loads(l) for l in open(ROOT / "evals/questions.jsonl")]
H = str(ROOT / "scripts/library.py")

def run(q, extra):
    out = subprocess.run([str(ROOT / ".venv/bin/python"), H, "search", q, "-n", "8", *extra], capture_output=True, text=True).stdout
    return [int(i) for i in re.findall(r"^\[(\d+)\]", out, re.M)]

def score(ids, expect):
    rows = [db.execute("SELECT tier, lower(title||' '||body) FROM meta WHERE id=?", (i,)).fetchone() for i in ids]
    on = [any(e in r[1] for e in expect) for r in rows]
    return (sum(on) / 8, sum(on) >= 3, any(r[0] == 1 for r in rows))

systems = {"ours": [], "ours-keyword": ["--mode", "keyword"], "moremozi-only": ["--kind", "coaching"], "notes-only": ["--kind", "notes", "--mode", "keyword"]}
res = {s: [] for s in systems}
for Q in Qs:
    for s, extra in systems.items():
        res[s].append(score(run(Q["q"], extra), Q["expect"]))
print(f"{'system':15} {'on-topic@8':>10} {'hit@8':>7} {'book@8':>7}")
for s, r in res.items():
    n = len(r)
    print(f"{s:15} {sum(x[0] for x in r)/n:10.0%} {sum(x[1] for x in r):4}/{n} {sum(x[2] for x in r):4}/{n}")
misses = [Q["id"] for Q, x in zip(Qs, res["ours"]) if not x[1]]
print("ours missed:", ", ".join(misses) or "none")
