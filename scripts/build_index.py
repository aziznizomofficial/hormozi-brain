#!/usr/bin/env python3
"""Build the Hormozi Brain index: SQLite FTS5 (BM25) + local embeddings, with source tiers,
book page numbers, promo stripping and near-duplicate collapsing.

Tier 1 books/playbooks  sources/books/text/*.txt           (pdftotext -raw, \\f = page break)
Tier 2 @AlexHormozi     sources/main-channel/md/*.md
Tier 3 interviews       sources/guest-interviews/md, sources/acq-channel/md
Tier 4 MoreMozi calls   sources/moremozi-ask-hormozi/corpus/transcripts
Tier 5 course notes     sources/acq-free-courses/*/*.md   (third-party written: routing only)
"""
import re, sqlite3, pathlib, sys, zlib, json
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, IDX = ROOT / "sources", ROOT / "index"
IDX.mkdir(exist_ok=True)
DB = IDX / "hormozi.db"
if DB.exists(): DB.unlink()

AD = re.compile(r"acquisition\.com/roadmap|free gift|link'?s in the description|spit it right back|"
                r"stages of growth they went|my team and i put together|book a call with my team|"
                r"human resources and finance|absolutely free|it's my gift to you|we'll do this in|"
                r"hours of us looking|subscribe|smash that", re.I)
def clean(t):
    t = re.sub(r"\[ ?__ ?\]", "[expletive]", t).replace(">>", " ")
    return " ".join(s for s in re.split(r"(?<=[.!?])\s+", t) if not AD.search(s)).strip()
def front(txt, key):
    m = re.search(rf'^{key}: "?(.*?)"?$', txt, re.M); return m.group(1) if m else ""

rows = []  # tier, kind, source, title, date, url, body
def videos(folder, tier, kind, label):
    for f in sorted(folder.glob("*.md")):
        txt = f.read_text(errors="ignore"); title, date = front(txt, "title"), front(txt, "published")
        for m in re.finditer(r"^## \[(\d+:\d+)\]\((.*?)\)\n+(.*?)(?=^## \[|\Z)", txt, re.M | re.S):
            b = clean(m.group(3).strip())
            if len(b) > 150: rows.append((tier, kind, label, f"{title} @ {m.group(1)}", date, m.group(2), b))

BOOK_NAMES = {  # file stem -> display name
    "100M-Leads-by-Alex-Hormozi": "$100M Leads",
    "100M_MONEY_MODELS_HOW_TO_MAKE_MONEY_by_Alex_Hormozi_epubNonfiction": "$100M Money Models",
    "$100M Offers Alex Hormozi": "$100M Offers",
    "$100M Offers The Lost Chapter Alex Hormozi_compressed": "$100M Offers — The Lost Chapter",
    "$100M Leads - 2 Bonus Chapters -- Alex Hormozi": "$100M Leads — Bonus Chapters",
}
def books(folder):
    for f in sorted(folder.glob("*.txt")):
        name = BOOK_NAMES.get(f.stem, f.stem)
        pages = f.read_text(errors="ignore").split("\f")
        buf, start = [], 1
        for i, p in enumerate(pages, 1):
            p = re.sub(r"Copyright © \d{4} by ACQUISITION\.COM LLC NOT FOR DISTRIBUTION", " ", p)
            buf.append(p.strip())
            words = sum(len(x.split()) for x in buf)
            if words >= 280 or i == len(pages):
                body = clean(re.sub(r"\s+", " ", " ".join(buf)))
                if len(body) > 150:
                    pr = f"p. {start}" if start == i else f"pp. {start}–{i}"
                    rows.append((1, "book", "Book / playbook", f"{name}, {pr}", "", f"{name} {pr}", body))
                buf, start = [], i + 1

def notes(paths):
    for f in paths:
        for i, p in enumerate(re.split(r"\n(?=#{1,3} )", f.read_text(errors="ignore"))):
            p = clean(p.strip())
            if len(p) > 150:
                head = p.splitlines()[0].lstrip("# ").strip()[:80] if p.startswith("#") else f"part {i+1}"
                rows.append((5, "notes", "Free-course notes (third-party)", f"{f.parent.name} / {f.stem} — {head}", "", str(f.relative_to(ROOT)), p))

books(SRC / "books/text")
videos(SRC / "main-channel/md", 2, "video", "Alex Hormozi (YouTube)")
videos(SRC / "guest-interviews/md", 3, "interview", "Guest interview")
videos(SRC / "acq-channel/md", 3, "video", "Acquisition.com (YouTube)")
videos(SRC / "moremozi-ask-hormozi/corpus/transcripts", 4, "coaching", "MoreMozi (YouTube)")
notes(sorted((SRC / "acq-free-courses").glob("*/*.md")))

# Near-duplicate collapse: sampled 8-word shingles; a chunk whose sample is >=60% already seen is dropped.
# Rows are processed best-first (tier, then longer body), so the canonical copy survives.
rows.sort(key=lambda r: (r[0], -len(r[6])))
seen, kept, dropped = set(), [], 0
for r in rows:
    w = re.findall(r"[a-z0-9']+", r[6].lower())
    sh = {zlib.crc32(" ".join(w[i:i+8]).encode()) for i in range(0, max(1, len(w) - 7))}
    samp = [h for h in sh if h % 4 == 0] or list(sh)[:5]
    if samp and sum(h in seen for h in samp) / len(samp) >= 0.6:
        dropped += 1; continue
    seen.update(samp); kept.append(r)

db = sqlite3.connect(DB)
db.execute("CREATE TABLE meta(id INTEGER PRIMARY KEY, tier INT, kind TEXT, source TEXT, title TEXT, date TEXT, url TEXT, body TEXT)")
db.execute("CREATE VIRTUAL TABLE fts USING fts5(title, body, content='meta', content_rowid='id', tokenize='porter unicode61')")
db.executemany("INSERT INTO meta(tier,kind,source,title,date,url,body) VALUES (?,?,?,?,?,?,?)", kept)
db.execute("INSERT INTO fts(fts) VALUES('rebuild')"); db.commit()
for s, n in db.execute("SELECT source, count(*) FROM meta GROUP BY source ORDER BY min(tier)"): print(f"{n:7}  {s}")
print(f"{len(kept):7}  chunks kept, {dropped} near-duplicates dropped")

if "--no-embed" not in sys.argv:
    import numpy as np
    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    ids, texts = zip(*db.execute("SELECT id, title || '. ' || body FROM meta ORDER BY id"))
    vecs = np.vstack(list(model.embed([t[:2000] for t in texts], batch_size=64))).astype("float16")
    np.save(IDX / "vectors.npy", vecs); np.save(IDX / "vector_ids.npy", np.array(ids, dtype="int32"))
    print(f"embedded {len(ids)} chunks -> {vecs.shape}")
