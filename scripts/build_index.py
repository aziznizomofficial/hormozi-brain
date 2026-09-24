#!/usr/bin/env python3
"""Build the Hormozi Brain search index (SQLite FTS5, BM25) from everything in sources/.

Sources:
  sources/moremozi-ask-hormozi/corpus/transcripts/*.md   MoreMozi channel (coaching calls)
  sources/main-channel/md/*.md                           @AlexHormozi channel (converted by vtt2md.py)
  sources/acq-free-courses/<course>/*.md                 free Acquisition.com courses (notes)
  sources/acq-official/*.txt                             official free PDFs (text)
  sources/books/**/*.{md,txt}                            books/playbooks you own (optional, drop in)
"""
import re, sqlite3, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, DB = ROOT / "sources", ROOT / "index" / "hormozi.db"
DB.parent.mkdir(exist_ok=True)
if DB.exists(): DB.unlink()

# Promo read that repeats in ~half of all videos. Drop any sentence containing a marker.
AD = re.compile(r"acquisition\.com/roadmap|free gift|link'?s in the description|spit it right back|"
                r"stages of growth they went|my team and i put together|book a call with my team|"
                r"human resources and finance|absolutely free|it's my gift to you|"
                r"we'll do this in|hours of us looking", re.I)
def clean(text):
    text = re.sub(r"\[ ?__ ?\]", "[expletive]", text)
    sents = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(s for s in sents if not AD.search(s)).strip()

db = sqlite3.connect(DB)
db.execute("CREATE VIRTUAL TABLE chunks USING fts5(source, title, date, url, body, tokenize='porter unicode61')")
rows = []
def front(txt, key):
    m = re.search(rf'^{key}: "?(.*?)"?$', txt, re.M); return m.group(1) if m else ""

def video_files(folder, label):
    for f in sorted(folder.glob("*.md")):
        txt = f.read_text(errors="ignore")
        title, date = front(txt, "title"), front(txt, "published")
        for m in re.finditer(r"^## \[(\d+:\d+)\]\((.*?)\)\n+(.*?)(?=^## \[|\Z)", txt, re.M | re.S):
            body = clean(m.group(3).replace(">>", " ").strip())
            if len(body) > 120:
                rows.append((label, f"{title} @ {m.group(1)}", date, m.group(2), body))

def doc_files(paths, label, url_prefix=""):
    for f in paths:
        txt = f.read_text(errors="ignore")
        name = f"{f.parent.name} / {f.stem}" if f.parent.name not in ("books", "acq-official") else f.stem
        # split on markdown headings, else every ~350 words
        parts = re.split(r"\n(?=#{1,3} )", txt)
        if len(parts) < 3:
            w = txt.split(); parts = [" ".join(w[i:i+350]) for i in range(0, len(w), 350)]
        for i, p in enumerate(parts):
            p = clean(p.strip())
            if len(p) > 120:
                head = p.splitlines()[0].lstrip("# ").strip()[:80] if p.startswith("#") else f"part {i+1}"
                rows.append((label, f"{name} — {head}", "", str(f.relative_to(ROOT)), p))

video_files(SRC / "moremozi-ask-hormozi/corpus/transcripts", "MoreMozi (YouTube)")
video_files(SRC / "main-channel/md", "Alex Hormozi (YouTube)")
doc_files(sorted((SRC / "acq-free-courses").glob("*/*.md")), "Acquisition.com free course")
doc_files(sorted((SRC / "acq-official").glob("*.txt")), "Acquisition.com free PDF")
if (SRC / "books").exists():
    doc_files(sorted(p for p in (SRC / "books").rglob("*") if p.suffix in (".md", ".txt")), "Book / playbook (your copy)")

db.executemany("INSERT INTO chunks VALUES (?,?,?,?,?)", rows); db.commit()
for src, n in db.execute("SELECT source, count(*) FROM chunks GROUP BY source"): print(f"{n:7}  {src}")
print(f"{len(rows):7}  total chunks -> {DB}")
