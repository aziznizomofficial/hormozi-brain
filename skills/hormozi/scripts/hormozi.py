#!/usr/bin/env python3
"""hormozi — search a paraphrased map of Alex Hormozi's books, playbooks, videos and coaching calls.
Every entry points to the original: book + page + section, or video + timestamp link. Needs only Python 3.9+.

  hormozi search "<question>" [-n 8] [--kind book|video|interview|coaching|case] [--mode auto|keyword|hybrid]
  hormozi get <id>                  one entry in full, plus what sits next to it in the same source
  hormozi frameworks [slug]         list his named models, or print one card
  hormozi video <id|url>            timestamped map of one video
  hormozi book [name]               list books, or the section map of one (headings + pages)
  hormozi verify <id>               show the original words behind an entry (video: live captions via yt-dlp;
                                    book: your own PDF in books/, if you have it)
  hormozi setup --semantic          optional: meaning-based search (installs fastembed into .venv, ~3 min)
  hormozi stats
"""
import argparse, hashlib, json, os, pathlib, re, sqlite3, subprocess, sys, tempfile, warnings
warnings.filterwarnings("ignore")   # numpy/Accelerate matmul and urllib3 LibreSSL notices would clutter agent output

ROOT = pathlib.Path(__file__).resolve().parent.parent   # the skill folder
KN, FW = ROOT / "knowledge", ROOT / "frameworks"
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if VENV_PY.exists() and pathlib.Path(sys.prefix).resolve() != (ROOT / ".venv").resolve() and not os.environ.get("HORMOZI_NO_VENV"):
    os.execv(str(VENV_PY), [str(VENV_PY), __file__] + sys.argv[1:])   # use the optional semantic-search env when installed
FILES = ["claims.jsonl", "cases.jsonl", "videos.jsonl", "books.jsonl"]
TIER_W = {1: 1.30, 2: 1.10, 3: 1.00, 4: 1.00}
KIND = {"book": ("book",), "video": ("main", "acq"), "interview": ("guest",), "coaching": ("coaching",)}
STOP = set("a an the and or but of to in on for with is are was be how do does i my me we our you your what why when should "
           "can it this that at as by from if so get about would he hormozi alex say says".split())
EMB = "BAAI/bge-small-en-v1.5"

def cache_dir():
    for d in (ROOT / ".cache", pathlib.Path.home() / ".cache/hormozi-brain"):
        try: d.mkdir(parents=True, exist_ok=True); t = d / ".w"; t.write_text(""); t.unlink(); return d
        except OSError: continue
    return pathlib.Path(tempfile.gettempdir())

def cards():
    """Framework card files, skipping hidden files (e.g. macOS ._ metadata in zips)."""
    return sorted(f for f in FW.glob("*.md") if not f.name.startswith("."))

def stamp():
    h = hashlib.sha1()
    for f in [KN / n for n in FILES] + cards():
        if f.exists(): h.update(f"{f.name}{f.stat().st_size}{int(f.stat().st_mtime)}".encode())
    return h.hexdigest()[:12]

def rows(name):
    p = KN / name
    return [json.loads(l) for l in p.open(encoding="utf-8")] if p.exists() else []

def label(at):
    p = [int(x) for x in at.split(":")]; s = p[-1] + 60 * p[-2] + (3600 * p[-3] if len(p) == 3 else 0)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"

def card_text(f):
    t = f.read_text(encoding="utf-8")
    m = re.search(r"## What it is\s*(.*?)(?=\n## |\Z)", t, re.S); w = re.search(r"## When to reach for it\s*(.*?)(?=\n## |\Z)", t, re.S)
    return t.splitlines()[0][2:], " ".join(t.splitlines()[:2]) + " " + (m.group(1) if m else "") + " " + (w.group(1) if w else "")

def build(db):
    db.executescript("""CREATE TABLE doc(id TEXT PRIMARY KEY, kind TEXT, src TEXT, tier INT, body TEXT, json TEXT);
        CREATE VIRTUAL TABLE fts USING fts5(body, meta, tokenize='porter unicode61');
        CREATE TABLE card(slug TEXT PRIMARY KEY, title TEXT, body TEXT);
        CREATE VIRTUAL TABLE cfts USING fts5(slug, title, body, tokenize='porter unicode61');""")
    def add(i, kind, src, tier, body, meta, obj):
        db.execute("INSERT INTO doc VALUES(?,?,?,?,?,?)", (i, kind, src, tier, body, json.dumps(obj, ensure_ascii=False)))
        db.execute("INSERT INTO fts(rowid, body, meta) VALUES(last_insert_rowid(), ?, ?)", (body, meta))
    for c in rows("claims.jsonl"):
        meta = " ".join([c.get("book", ""), c.get("section", ""), c.get("title", ""), " ".join(c.get("frameworks", [])).replace("-", " ")])
        add(c["id"], "claim", c["src"], c["tier"], c["text"], meta, c)
    for c in rows("cases.jsonl"):
        body = f"{c['business']}. {c['numbers']}. {c['question']} {c['diagnosis']} " + " ".join(c["advice"])
        add(c["id"], "case", c["src"], c["tier"], body, c["title"], c)
    for v in rows("videos.jsonl"):
        for s in v["segments"]:
            if s["topic"] in ("intro", "promo", "off-topic"): continue
            add(f"{v['video']}@{s['at']}", "segment", v["src"], 4, s["topic"], v["title"] + " " + " ".join(s["tags"]),
                {"video": v["video"], "title": v["title"], "channel": v["channel"], "date": v["date"], "at": s["at"], "topic": s["topic"],
                 "url": f"{v['url']}&t={sum(int(x) * 60 ** k for k, x in enumerate(reversed(s['at'].split(':'))))}s"})
    for f in cards():
        title, body = card_text(f)
        db.execute("INSERT INTO card VALUES(?,?,?)", (f.stem, title, body)); db.execute("INSERT INTO cfts VALUES(?,?,?)", (f.stem.replace("-", " "), title, body))
    db.commit()

def open_db():
    p = cache_dir() / f"knowledge-{stamp()}.db"
    if not p.exists():
        for old in p.parent.glob("knowledge-*.db"): old.unlink()
        tmp = p.with_suffix(".tmp"); tmp.unlink(missing_ok=True)
        d = sqlite3.connect(tmp); build(d); d.close(); tmp.rename(p)
    return sqlite3.connect(p)

def terms(q): return [t for t in re.findall(r"[a-z0-9$%']+", q.lower()) if t not in STOP and len(t) > 1]

def fts_query(ts, op): return f" {op} ".join(f'"{t}"' for t in ts)

def keyword(db, q, kinds, k):
    """Two ranked lists: entries matching every term, then entries matching any term."""
    ts = terms(q); out = []
    if not ts: return [[], []]
    srcs = ",".join(f"'{s}'" for s in kinds) if kinds else None
    for op in ("AND", "OR"):
        sql = ("SELECT doc.rowid FROM fts JOIN doc ON doc.rowid = fts.rowid WHERE fts MATCH ?"
               + (f" AND doc.src IN ({srcs})" if srcs else "") + " ORDER BY bm25(fts, 1.0, 0.4) LIMIT ?")
        out.append([i for (i,) in db.execute(sql, (fts_query(ts, op), k))])
    return out

# ---- optional semantic layer (fastembed + numpy in .venv) ----
def have_semantic():
    try: import numpy, fastembed  # noqa
    except ImportError: return False
    return True

_model = None
def embed(texts, query=False):
    global _model
    import numpy as np
    from fastembed import TextEmbedding
    _model = _model or TextEmbedding(EMB)
    f = _model.query_embed if query else _model.passage_embed
    return np.vstack(list(f(texts))).astype("float32")

def vectors(db):
    import numpy as np
    p = cache_dir() / f"vectors-{stamp()}.npz"
    if not p.exists():
        for old in p.parent.glob("vectors-*.npz"): old.unlink()
        ids, texts = zip(*db.execute("SELECT rowid, body FROM doc ORDER BY rowid"))
        slugs, ctexts = zip(*db.execute("SELECT slug, title || '. ' || body FROM card ORDER BY slug")) if db.execute("SELECT count(*) FROM card").fetchone()[0] else ((), ())
        print(f"(one-time: embedding {len(ids)} entries for meaning-based search, a few minutes…)", file=sys.stderr)
        np.savez(p, ids=np.array(ids), V=embed(list(texts)).astype("float16"), slugs=np.array(slugs), C=embed(list(ctexts)) if ctexts else np.zeros((0, 384)))
    z = np.load(p); return z["ids"], z["V"].astype("float32"), list(z["slugs"]), z["C"]

def semantic(db, q, kinds, k):
    import numpy as np
    ids, V, _, _ = vectors(db); order = np.argsort(-np.nan_to_num(V.astype('float64') @ embed([q], True)[0]))
    if not kinds: return [int(ids[i]) for i in order[:k]]
    ok = {r for (r,) in db.execute(f"SELECT rowid FROM doc WHERE src IN ({','.join(repr(s) for s in kinds)})")}
    return [int(ids[i]) for i in order[: k * 20] if int(ids[i]) in ok][:k]

def cards_for(db, q, mode, k=3):
    ts = terms(q)
    kw = [s for (s,) in db.execute("SELECT card.slug FROM cfts JOIN card ON card.rowid = cfts.rowid WHERE cfts MATCH ? "
                                   "ORDER BY bm25(cfts, 3.0, 2.0, 1.0) LIMIT 10", (fts_query(ts, "OR"),))] if ts else []
    if mode != "hybrid": return kw[:k]
    import numpy as np
    _, _, slugs, C = vectors(db)
    if not len(slugs): return kw[:k]
    sc = {s: 1 / (60 + r) for r, s in enumerate(kw)}
    for r, i in enumerate(np.argsort(-np.nan_to_num(C.astype('float64') @ embed([q], True)[0]))[:10]): sc[slugs[i]] = sc.get(slugs[i], 0) + 1 / (60 + r)
    return sorted(sc, key=lambda s: -sc[s])[:k]

def pointer(o):
    if o.get("src") == "book": return f"{o['book']}, p. {o['page']}" + (f" — {o['section']}" if o.get("section") else "")
    return f"{o['title']} @ {label(o['at'])} · {o['channel']}{' · ' + o['date'] if o.get('date') else ''}\n    {o['url']}"

def show_hit(i, kind, o):
    if kind == "claim": head = f"({o['type']}) {o['text']}"
    elif kind == "case": head = f"CASE: {o['business']}" + (f" | {o['numbers']}" if o["numbers"] else "") + f"\n    stuck on: {o['question']}\n    his diagnosis: {o['diagnosis']}\n    his advice: " + "; ".join(o["advice"])
    else: head = f"(video map) {o['topic']}"
    print(f"[{i}] {head}\n    {pointer(o) if kind != 'segment' else o['title'] + ' @ ' + label(o['at']) + ' · ' + o['channel'] + chr(10) + '    ' + o['url']}\n")

def search(a):
    db = open_db(); q = " ".join(a.q)
    mode = a.mode if a.mode != "auto" else ("hybrid" if have_semantic() else "keyword")
    kinds = KIND.get(a.kind) if a.kind and a.kind != "case" else None
    cs = cards_for(db, q, mode)
    if cs:
        print("Framework cards (read first: hormozi frameworks <slug>):")
        for s in cs: print(f"  {s:34} {db.execute('SELECT title FROM card WHERE slug=?', (s,)).fetchone()[0]}")
        print()
    all_terms, any_term = keyword(db, q, kinds, 80)
    lists = [(all_terms, 2.0), (any_term, 1.0)] + ([(semantic(db, q, kinds, 80), 2.0)] if mode == "hybrid" else [])
    score = {}
    for lst, w in lists:
        for r, i in enumerate(lst): score[i] = score.get(i, 0) + w / (60 + r)
    shown, per = 0, {}
    for i in sorted(score, key=lambda i: -score[i] * TIER_W.get(db.execute("SELECT tier FROM doc WHERE rowid=?", (i,)).fetchone()[0], 1)):
        did, kind, src, tier, body, js = db.execute("SELECT * FROM doc WHERE rowid=?", (i,)).fetchone(); o = json.loads(js)
        if a.kind == "case" and kind != "case": continue
        key = o.get("book") or o.get("video")
        if per.get(key, 0) >= 2: continue
        per[key] = per.get(key, 0) + 1; show_hit(did, kind, o); shown += 1
        if shown >= a.n: break
    if not shown: print("no results — try other words, or: hormozi frameworks")
    if mode == "keyword" and not have_semantic(): print("(keyword search; for meaning-based search run: hormozi setup --semantic)")

def get(a):
    db = open_db(); r = db.execute("SELECT kind, json FROM doc WHERE id=?", (a.id,)).fetchone()
    if not r: sys.exit("no such id (ids look like main-XXXX#3, book-100M-Offers-p060#2, coaching-XXXX#case1)")
    kind, o = r[0], json.loads(r[1]); show_hit(a.id, kind, o)
    if o.get("src") == "book":
        near = [json.loads(j) for (j,) in db.execute("SELECT json FROM doc WHERE kind='claim' AND src='book' AND id != ?", (a.id,))]
        near = [n for n in near if n["book"] == o["book"] and abs(n["page"] - o["page"]) <= 2]
        if near: print("Nearby in the same book:"); [print(f"  p. {n['page']}: {n['text']}  [{n['id']}]") for n in sorted(near, key=lambda n: n['page'])]
        return
    v = next((v for v in rows("videos.jsonl") if v["video"] == o["video"]), None)
    if v:
        secs = lambda t: sum(int(x) * 60 ** k for k, x in enumerate(reversed(t.split(":"))))
        t0 = secs(o["at"]); print("Around it in the video:")
        for s in v["segments"]:
            if abs(secs(s["at"]) - t0) <= 270: print(f"  {label(s['at'])}  {s['topic']}")
        near = [json.loads(j) for (j,) in db.execute("SELECT json FROM doc WHERE kind='claim' AND id LIKE ? AND id != ?", (a.id.split("#")[0] + "#%", a.id))]
        near = [n for n in near if abs(secs(n["at"]) - t0) <= 270]
        if near: print("Other points he makes there:"); [print(f"  {label(n['at'])}  {n['text']}  [{n['id']}]") for n in near]

def frameworks(a):
    files = cards()
    if not a.name:
        for f in files: print(f"{f.stem:40} {f.read_text(encoding='utf-8').splitlines()[0][2:]}")
        return
    hits = [f for f in files if f.stem == a.name] or [f for f in files if a.name.lower().replace(" ", "-") in f.stem]
    print(hits[0].read_text(encoding="utf-8") if hits else "no framework card matches; try: hormozi frameworks")

def video(a):
    vid = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", a.id); vid = vid.group(1) if vid else a.id
    v = next((v for v in rows("videos.jsonl") if v["video"] == vid), None)
    if not v: sys.exit("video not in the map")
    print(f"{v['title']}\n{v['channel']} · {v['date']} · {v['url']}\n\n{v['summary']}\n")
    for s in v["segments"]: print(f"  {label(s['at']):>8}  {s['topic']}")

def book(a):
    bs = rows("books.jsonl")
    if not a.name:
        for b in bs: print(f"{b['slug']:32} {b['book']}  ({len(b['sections'])} sections)")
        return
    b = next((b for b in bs if a.name.lower() in (b["slug"] + " " + b["book"]).lower()), None)
    if not b: sys.exit("no such book; run: hormozi book")
    print(b["book"]); [print(f"  p. {s['page']:>3}  {s['heading']}  — {s['topic']}") for s in b["sections"]]

def verify(a):
    db = open_db(); r = db.execute("SELECT json FROM doc WHERE id=?", (a.id,)).fetchone()
    if not r: sys.exit("no such id")
    o = json.loads(r[0]); print(f"Entry: {o.get('text') or o.get('topic') or o.get('question')}\nSource: {pointer(o)}\n")
    if o.get("src") == "book": return verify_book(o)
    secs = lambda t: sum(int(x) * 60 ** k for k, x in enumerate(reversed(t.split(":"))))
    t0 = secs(o["at"]); exe = next((p for p in (VENV_PY.parent / "yt-dlp", "yt-dlp") if subprocess.run(["which", str(p)], capture_output=True).returncode == 0 or pathlib.Path(p).exists()), None)
    if not exe: sys.exit("Install yt-dlp to read the original captions (pip install yt-dlp), or open the link above.")
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([str(exe), "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en,en-orig", "--sub-format", "vtt",
                        "-o", f"{d}/v.%(ext)s", f"https://www.youtube.com/watch?v={o['video']}"], capture_output=True, timeout=180)
        vtt = next(pathlib.Path(d).glob("*.vtt"), None)
        if not vtt: sys.exit("YouTube did not return captions (rate limit or bot check). Open the link above instead.")
        seen, out = set(), []
        for m in re.finditer(r"(\d+):(\d\d):(\d\d)\.\d+ --> .*?\n(.*?)(?=\n\n|\Z)", vtt.read_text(errors="ignore"), re.S):
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            if t0 - 5 <= t <= t0 + 100:
                for line in re.sub(r"<[^>]+>", "", m.group(4)).splitlines():
                    if line.strip() and line not in seen: seen.add(line); out.append(line.strip())
        print("Original captions, fetched live from YouTube (~90 s from the timestamp):\n\n" + " ".join(out))

def verify_book(o):
    pdfs = list((ROOT / "books").glob("*.pdf")) if (ROOT / "books").exists() else []
    name = re.sub(r"[^a-z0-9]", "", o["book"].lower().replace("$100m", "100m"))
    pdf = next((p for p in pdfs if name[:14] in re.sub(r"[^a-z0-9]", "", p.stem.lower())), None)
    if not pdf: sys.exit(f"Open your copy of {o['book']} at page {o['page']}" + (f" (section “{o['section']}”)" if o.get("section") else "")
                         + ". To check automatically, put your PDF in books/ (never committed).")
    try: r = subprocess.run(["pdftotext", "-raw", "-f", str(o["page"]), "-l", str(o["page"]), str(pdf), "-"], capture_output=True, text=True); print(r.stdout)
    except FileNotFoundError:
        try:
            from pypdf import PdfReader; print(PdfReader(str(pdf)).pages[o["page"] - 1].extract_text())
        except ImportError: sys.exit("Install poppler (pdftotext) or pypdf to read your PDF, or open it at the page above.")

def setup(a):
    if not a.semantic: sys.exit("usage: hormozi setup --semantic")
    if not VENV_PY.exists(): subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
    subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "fastembed", "numpy", "yt-dlp"], check=True)
    subprocess.run([str(VENV_PY), __file__, "search", "warm up the index"], check=True, stdout=subprocess.DEVNULL)
    print("semantic search ready")

def stats(a):
    db = open_db()
    for kind, src, n in db.execute("SELECT kind, src, count(*) FROM doc GROUP BY kind, src ORDER BY kind, src"): print(f"{n:7}  {kind:8} {src}")
    print(f"{db.execute('SELECT count(*) FROM card').fetchone()[0]:7}  framework cards")

ap = argparse.ArgumentParser(prog="hormozi"); sub = ap.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("search"); s.add_argument("q", nargs="+"); s.add_argument("-n", type=int, default=8)
s.add_argument("--kind", choices=["book", "video", "interview", "coaching", "case"]); s.add_argument("--mode", default="auto", choices=["auto", "hybrid", "keyword"])
for name, fn in (("get", "id"), ("verify", "id"), ("video", "id")): sub.add_parser(name).add_argument(fn)
sub.add_parser("frameworks").add_argument("name", nargs="?"); sub.add_parser("book").add_argument("name", nargs="?")
sub.add_parser("setup").add_argument("--semantic", action="store_true"); sub.add_parser("stats")
a = ap.parse_args()
{"search": search, "get": get, "frameworks": frameworks, "video": video, "book": book, "verify": verify, "setup": setup, "stats": stats}[a.cmd](a)
