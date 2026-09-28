#!/usr/bin/env python3
"""Draft framework cards for named models the extractors found that have no card yet.

  cards.py candidates [--min 4]      list candidate names (merged variants, mention counts, closest existing card)
  cards.py draft [--min 4] [--max 40] --backend codex:gpt-6-astra:high
                                     draft cards from the gated knowledge layer, copy-gate them, write new cards
Reads skills/hormozi/knowledge/claims.jsonl (so run assemble.py first) plus the raw "new:<Name>" tags in build/distill.
Writes skills/hormozi/frameworks/<slug>.md and scripts/distill/card_aliases.json (tag → slug, used by assemble.py).
"""
import argparse, collections, glob, json, pathlib, re, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import distill as D, assemble as A

ROOT = D.ROOT; FW = ROOT / "skills/hormozi/frameworks"; KN = ROOT / "skills/hormozi/knowledge"
ALIASES = pathlib.Path(__file__).parent / "card_aliases.json"
norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def raw_tags():
    """normalized new-name → list of (unit, claim text) from raw distill outputs."""
    tags = collections.defaultdict(list)
    for run in ("books", "videos"):
        for f in glob.glob(str(ROOT / f"build/distill/{run}/*.json")):
            r = json.load(open(f))
            for c in r["out"].get("claims", []):
                for t in c.get("frameworks") or []:
                    if isinstance(t, str) and t.startswith("new:"): tags[norm(t[4:])].append((r["unit"], c.get("text", "")))
    return tags

def candidates(model, min_n):
    tags = raw_tags(); names = sorted(tags)
    V = np.vstack(list(model.query_embed(names))) if names else np.zeros((0, 384))
    # merge variants: greedy by frequency, cosine >= 0.86
    order = sorted(range(len(names)), key=lambda i: -len(tags[names[i]])); groups, taken = [], set()
    for i in order:
        if i in taken: continue
        g = [j for j in order if j not in taken and float(V[i] @ V[j]) >= 0.86]; taken.update(g); groups.append(g)
    cards = sorted(FW.glob("*.md"))
    ctext = [" ".join(c.read_text().splitlines()[:2]) for c in cards]
    C = np.vstack(list(model.passage_embed(ctext)))
    out = []
    for g in groups:
        mentions = [m for j in g for m in tags[names[j]]]
        units = {u.split("-p")[0] if u.startswith("book-") else re.sub(r"-p\d+$", "", u) for u, _ in mentions}
        if len(mentions) < min_n or len(units) < 2: continue
        sims = C @ V[g[0]]; best = int(np.argmax(sims))
        out.append({"name": names[g[0]], "variants": [names[j] for j in g], "mentions": len(mentions), "sources": len(units),
                    "closest": cards[best].stem, "closest_sim": round(float(sims[best]), 2)})
    return out

def gather(model, cand, claims, k=24):
    """Claims tagged with any variant, plus the nearest claims by meaning (all already gated + pointed)."""
    q = np.vstack(list(model.query_embed([cand["name"]])))[0]
    texts = [c["text"] for c in claims]
    global _CV
    if "_CV" not in globals(): _CV = np.vstack(list(model.passage_embed(texts)))
    sims = _CV @ q; idx = list(np.argsort(-sims)[:k])
    return [claims[i] for i in idx if sims[i] > 0.55]

def pointer(c):
    return f"{c['book']}, p. {c['page']}" + (f" ({c['section']})" if c.get("section") else "") if c["src"] == "book" else f"[{c['title']} @ {c['at']}]({c['url']})"

PROMPT = """You write framework cards for a public, copyright-safe study tool about Alex Hormozi's business models.
Write ONE card per candidate below, using ONLY the paraphrased claims given for it (each already points to its source).
If a candidate's claims do not describe a coherent named model of his (just a phrase, a one-off remark, or a duplicate of the
existing card named in "closest"), return it with "skip": true and a one-line reason.

Card format, exactly like this example (Markdown):
---
{example}
---
Rules: category is one of offer, pricing, leads, ads, sales, retention, money-models, scaling, hiring, operations, mindset, content, brand.
Sources section: list ONLY pointers that appear in the claims you were given, copied exactly. Plain English, your own words,
no quotation marks, never first person as him. Keep numbers exactly as the claims give them. Omit a section rather than invent it.

CANDIDATES (JSON):
{items}

Return {{"cards":[{{"name":..., "skip": false, "slug": kebab-case, "markdown": full card}} or {{"name":..., "skip": true, "reason":...}}]}}
"""

def draft(a, model):
    claims = [json.loads(l) for l in (KN / "claims.jsonl").open()]
    cands = [c for c in candidates(model, a.min) if c["closest_sim"] < 0.9 and (not a.only or c["name"] in a.only.split(","))][: a.max]
    print(len(cands), "candidates to draft")
    example = (FW / "value-equation.md").read_text()
    work = ROOT / "build/cards"; work.mkdir(parents=True, exist_ok=True)
    aliases = json.loads(ALIASES.read_text()) if ALIASES.exists() else {}
    src_grams = None; made = 0
    for b in range(0, len(cands), 5):
        batch = cands[b:b + 5]
        items = [{"name": c["name"], "variants": c["variants"], "closest_existing_card": c["closest"],
                  "claims": [{"text": x["text"], "pointer": pointer(x)} for x in gather(model, c, claims)]} for c in batch]
        txt, _ = D.call(a.backend, PROMPT.format(example=example, items=json.dumps(items, ensure_ascii=False, indent=1)), work)
        res = D.parse_json(txt)["cards"]
        if src_grams is None: src_grams = all_source_grams()
        for c, cand in zip(res, batch):
            if c.get("skip"): print(f"  skip {c['name']}: {c.get('reason','')}"); continue
            slug = re.sub(r"[^a-z0-9-]+", "-", c["slug"].lower()).strip("-")
            body = c["markdown"].strip() + "\n"
            prose = body.split("\n## Sources")[0]
            if longest(prose, src_grams) >= 8:
                (work / "dropped").mkdir(exist_ok=True); (work / "dropped" / f"{slug}.md").write_text(body)
                for v in cand["variants"]: aliases[v] = slug
                print(f"  DROP {slug}: copies source text (saved to build/cards/dropped for fix_copies.py)"); continue
            if (FW / f"{slug}.md").exists(): print(f"  exists {slug}"); continue
            (FW / f"{slug}.md").write_text(body); made += 1; print(f"  + {slug}")
            for v in cand["variants"]: aliases[v] = slug
    ALIASES.write_text(json.dumps(aliases, indent=1, sort_keys=True)); print(made, "new cards")

def all_source_grams():
    import sqlite3, zlib
    g = set(); W = D.words
    for f in (ROOT / "sources/books/paged").glob("*.md"):
        w = W(f.read_text(errors="ignore")); g.update(zlib.crc32(" ".join(w[i:i + 8]).encode()) for i in range(len(w) - 7))
    for (b,) in sqlite3.connect(ROOT / "index/hormozi.db").execute("SELECT body FROM meta WHERE tier BETWEEN 2 AND 4"):
        w = W(b); g.update(zlib.crc32(" ".join(w[i:i + 8]).encode()) for i in range(len(w) - 7))
    return g

def longest(text, g):
    import zlib
    w = D.words(text); return 8 if any(zlib.crc32(" ".join(w[i:i + 8]).encode()) in g for i in range(len(w) - 7)) else 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("candidates"); x.add_argument("--min", type=int, default=4)
    x = sub.add_parser("draft"); x.add_argument("--min", type=int, default=4); x.add_argument("--max", type=int, default=40)
    x.add_argument("--backend", default="codex:gpt-6-astra:high"); x.add_argument("--only", help="comma-separated candidate names")
    a = ap.parse_args()
    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    if a.cmd == "candidates":
        for c in candidates(model, a.min): print(f"{c['mentions']:4} m {c['sources']:3} src  {c['name']:45} closest={c['closest']} ({c['closest_sim']})  {c['variants'][1:4]}")
    else: draft(a, model)
