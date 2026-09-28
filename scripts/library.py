#!/usr/bin/env python3
"""library.py (owner-only, needs the private index built by rebuild.sh) — search Alex Hormozi's books, playbooks, videos and interviews.

  library.py search "<question>" [-n 8] [--kind book|video|interview|coaching|notes] [--mode hybrid|keyword]
  hormozi get <id> [--around 1]        full text of a chunk (+ neighbouring chunks of the same source)
  hormozi frameworks [name]            list framework cards, or print one
  hormozi stats
"""
import argparse, re, sqlite3, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
IDX = ROOT / "index"
db = sqlite3.connect(IDX / "hormozi.db")
TIER_W = {1: 1.30, 2: 1.10, 3: 1.00, 4: 1.00, 5: 0.50}
STOP = set("a an the and or but of to in on for with is are was be how do does i my me we our you your what why when should "
           "can it this that at as by from if so get about would he hormozi alex say says".split())

def keyword(q, kind, k):
    terms = [t for t in re.findall(r"[a-z0-9$%']+", q.lower()) if t not in STOP]
    out = []
    for j in (" AND ", " OR "):
        if not terms: break
        sql = ("SELECT meta.id FROM fts JOIN meta ON meta.id = fts.rowid WHERE fts MATCH ? AND meta.kind LIKE ? "
               "ORDER BY bm25(fts, 2.0, 1.0) LIMIT ?")
        for (i,) in db.execute(sql, (j.join(f'"{t}"' for t in terms), kind, k)):
            if i not in out: out.append(i)
    return out

def semantic(q, kind, k):
    vp = IDX / "vectors.npy"
    if not vp.exists(): return []
    import numpy as np
    from fastembed import TextEmbedding
    V = np.load(vp).astype("float32"); ids = np.load(IDX / "vector_ids.npy")
    qv = embed_query(q)
    order = np.argsort(-(V @ qv))
    if kind == "%": return [int(ids[i]) for i in order[:k]]
    allowed = {i for (i,) in db.execute("SELECT id FROM meta WHERE kind LIKE ?", (kind,))}
    return [int(ids[i]) for i in order[:k * 20] if int(ids[i]) in allowed][:k]

_model = None
def embed_query(q):
    global _model
    from fastembed import TextEmbedding
    _model = _model or TextEmbedding("BAAI/bge-small-en-v1.5")
    return next(_model.query_embed([q])).astype("float32")

def card_vectors():
    """Embed each card's title + aliases + 'What it is' once; cached in index/cards.npz, rebuilt when cards change."""
    import numpy as np
    files = sorted((ROOT / "skills/hormozi/frameworks").glob("*.md")); cache = IDX / "cards.npz"
    stamp = max((f.stat().st_mtime for f in files), default=0)
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        if float(z["stamp"]) == stamp and len(z["slugs"]) == len(files): return list(z["slugs"]), list(z["titles"]), z["V"]
    from fastembed import TextEmbedding
    texts, slugs, titles = [], [], []
    for f in files:
        t = f.read_text(); secs = [re.search(rf"## {h}\s*(.*?)(?=\n## |\Z)", t, re.S) for h in ("What it is", "When to reach for it")]
        texts.append(" ".join(t.splitlines()[:2]) + " " + " ".join(m.group(1) for m in secs if m)); slugs.append(f.stem); titles.append(t.splitlines()[0][2:])
    global _model
    _model = _model or TextEmbedding("BAAI/bge-small-en-v1.5")
    V = np.vstack(list(_model.passage_embed(texts))).astype("float32")
    np.savez(cache, stamp=stamp, slugs=np.array(slugs), titles=np.array(titles), V=V)
    return slugs, titles, V

def cards_for(q, k=3):
    import numpy as np
    slugs, titles, V = card_vectors()
    if not slugs: return []
    sims = V @ embed_query(q)
    terms = {t[:5] for t in re.findall(r"[a-z0-9']+", q.lower()) if t not in STOP and len(t) > 2}
    kw = np.array([len(terms & {w[:5] for w in re.findall(r"[a-z0-9']+", (s + " " + t).lower())}) for s, t in zip(slugs, titles)])
    score = sims + 0.05 * kw
    return [(float(score[i]), slugs[i], titles[i]) for i in np.argsort(-score)[:k]]

def search(a):
    q, kind = " ".join(a.q), a.kind or "%"
    cs = cards_for(q)
    if cs: print("Framework cards (read first: hormozi frameworks <slug>):\n" + "\n".join(f"  {c[1]:32} {c[2]}" for c in cs) + "\n")
    lists = [keyword(q, kind, 60)] + ([semantic(q, kind, 60)] if a.mode == "hybrid" else [])
    score = {}
    for lst in lists:
        for r, i in enumerate(lst): score[i] = score.get(i, 0) + 1 / (60 + r)
    tiers = dict(db.execute(f"SELECT id, tier FROM meta WHERE id IN ({','.join(map(str, score)) or 0})"))
    ranked = sorted(score, key=lambda i: -score[i] * TIER_W[tiers[i]])
    shown, per_source = 0, {}
    for i in ranked:
        tier, kind_, src, title, date, url, body = db.execute("SELECT tier,kind,source,title,date,url,body FROM meta WHERE id=?", (i,)).fetchone()
        key = re.sub(r"( @ \d+:\d+|, pp?\. .*)$", "", title)
        if per_source.get(key, 0) >= 2: continue            # at most 2 chunks per video/book per query
        per_source[key] = per_source.get(key, 0) + 1
        words = body.split(); snip = " ".join(words[:70]) + (" …" if len(words) > 70 else "")
        print(f"[{i}] {title}\n    tier {tier} · {src}{' · ' + date if date else ''}\n    {url}\n    {snip}\n")
        shown += 1
        if shown >= a.n: break
    if not shown: print("no results")

def get(a):
    row = db.execute("SELECT tier,source,title,url FROM meta WHERE id=?", (a.id,)).fetchone()
    if not row: sys.exit("no such id")
    key = re.sub(r"( @ \d+:\d+|, pp?\. .*)$", "", row[2])
    for i in range(a.id - a.around, a.id + a.around + 1):
        r = db.execute("SELECT title,url,body FROM meta WHERE id=?", (i,)).fetchone()
        if r and re.sub(r"( @ \d+:\d+|, pp?\. .*)$", "", r[0]) == key:
            print(f"### [{i}] {r[0]}\n{r[1]}\n\n{r[2]}\n")

def frameworks(a):
    d = ROOT / "skills/hormozi/frameworks"
    files = sorted(d.glob("*.md")) if d.exists() else []
    if not a.name:
        for f in files:
            first = next((l for l in f.read_text().splitlines() if l.startswith("# ")), f.stem)
            print(f"{f.stem:40} {first[2:]}")
        return
    hits = [f for f in files if a.name.lower().replace(" ", "-") in f.stem]
    print(hits[0].read_text() if hits else "no framework card matches; try: hormozi frameworks")

ap = argparse.ArgumentParser(prog="hormozi"); sub = ap.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("search"); s.add_argument("q", nargs="+"); s.add_argument("-n", type=int, default=8)
s.add_argument("--kind", choices=["book", "video", "interview", "coaching", "notes"]); s.add_argument("--mode", default="hybrid", choices=["hybrid", "keyword"])
g = sub.add_parser("get"); g.add_argument("id", type=int); g.add_argument("--around", type=int, default=0)
f = sub.add_parser("frameworks"); f.add_argument("name", nargs="?")
sub.add_parser("stats")
a = ap.parse_args()
if a.cmd == "search": search(a)
elif a.cmd == "get": get(a)
elif a.cmd == "frameworks": frameworks(a)
else:
    for s_, n in db.execute("SELECT source, count(*) FROM meta GROUP BY source ORDER BY min(tier)"): print(f"{n:7}  {s_}")
