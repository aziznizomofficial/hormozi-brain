#!/usr/bin/env python3
"""Rewrite only the lines of Markdown cards that repeat 8+ consecutive words of the private sources, then re-gate.

  fix_copies.py <card.md>... [--out DIR] [--backend codex:gpt-6-astra:high] [--rounds 2]
Clean cards are written to --out (default: skills/hormozi/frameworks). Needs the private sources.
"""
import argparse, json, pathlib, sys, zlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import distill as D, cards as C

def flagged(text, g):
    head = text.split("\n## Sources")[0]; out = []
    for ln, line in enumerate(text.split("\n")):
        if ln >= len(head.split("\n")) or line.startswith(("# ", "slug:")): continue
        w = D.words(line); spans = []; i = 0
        while i <= len(w) - 8:
            if zlib.crc32(" ".join(w[i:i + 8]).encode()) in g:
                j = i + 8
                while j < len(w) and zlib.crc32(" ".join(w[j - 7:j + 1]).encode()) in g: j += 1
                spans.append(" ".join(w[i:j])); i = j
            else: i += 1
        if spans: out.append({"line_no": ln, "line": line, "copied_spans": spans})
    return out

PROMPT = """Rewrite each Markdown line below so it says exactly the same thing (same facts, numbers, conditions, page references,
same Markdown shape) but shares no run of 6+ consecutive words with its copied_spans. Names, titles, numbers and coined
framework names may stay. Plain English, no quotation marks, refer to him as "he" or "Hormozi".
Return {{"rewrites":[{{"line_no":int,"new_line":str}}]}} for every item.
ITEMS:
{items}"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cards", nargs="+"); ap.add_argument("--out", default=str(D.ROOT / "skills/hormozi/frameworks"))
    ap.add_argument("--backend", default="codex:gpt-6-astra:high"); ap.add_argument("--rounds", type=int, default=2); a = ap.parse_args()
    g = C.all_source_grams(); work = D.OUT / "_work"; work.mkdir(parents=True, exist_ok=True)
    for path in map(pathlib.Path, a.cards):
        text = path.read_text()
        for r in range(a.rounds):
            fl = flagged(text, g)
            if not fl: break
            txt, _ = D.call(a.backend, PROMPT.format(items=json.dumps(fl, ensure_ascii=False, indent=1)), work)
            lines = text.split("\n")
            for rw in D.parse_json(txt)["rewrites"]:
                if 0 <= rw["line_no"] < len(lines): lines[rw["line_no"]] = rw["new_line"]
            text = "\n".join(lines)
        left = flagged(text, g)
        if left: print(f"  still copying, not written: {path.name} ({len(left)} lines)"); continue
        (pathlib.Path(a.out) / path.name).write_text(text); print(f"  + {path.name}")
