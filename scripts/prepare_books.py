#!/usr/bin/env python3
"""PDFs in sources/books/drive -> clean text (pdftotext -raw fixes the ligature '!' bug) + page-marked copies."""
import pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parent.parent; B = ROOT / "sources/books"
SKIP = re.compile(r"ALL BOOKS|^\$100M Money Models - How To Make Money_", re.I)   # combined dump / weaker duplicate
NAMES = {"100M-Leads-by-Alex-Hormozi": "100M-Leads", "100M_MONEY_MODELS_HOW_TO_MAKE_MONEY_by_Alex_Hormozi_epubNonfiction": "100M-Money-Models",
         "$100M Offers Alex Hormozi": "100M-Offers", "$100M Offers The Lost Chapter Alex Hormozi_compressed": "100M-Offers-Lost-Chapter",
         "$100M Leads - 2 Bonus Chapters -- Alex Hormozi": "100M-Leads-Bonus-Chapters"}
for d in ("text", "paged"): (B / d).mkdir(parents=True, exist_ok=True)
for pdf in sorted((B / "drive").glob("*.pdf")):
    if SKIP.search(pdf.name): continue
    txt = B / "text" / f"{pdf.stem}.txt"
    if not txt.exists(): subprocess.run(["pdftotext", "-raw", str(pdf), str(txt)], check=True)
    name = NAMES.get(pdf.stem, re.sub(r"[^A-Za-z0-9]+", "-", pdf.stem).strip("-"))
    pages = txt.read_text(errors="ignore").split("\f")
    (B / "paged" / f"{name}.md").write_text("".join(f"\n=== p. {i} ===\n{p.strip()}\n" for i, p in enumerate(pages, 1) if p.strip()))
print("books ready:", len(list((B / "text").glob("*.txt"))))
