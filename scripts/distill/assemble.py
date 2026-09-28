#!/usr/bin/env python3
"""Turn distill runs into the shipped knowledge layer (knowledge/*.jsonl). Runs on the owner's machine only,
because the two gates below need the original text:

  copy gate     drop any text that reproduces >= 8 consecutive words of its source
  pointer gate  embed each claim against every chunk/page of its unit; a pointer outside the top 3 is widened to
                the best neighbour, re-pointed when the best chunk wins clearly, or dropped when nothing matches

  assemble.py [--videos build/distill/videos] [--books build/distill/books]
"""
import argparse, collections, json, pathlib, re, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import distill as D

ROOT = D.ROOT; K = ROOT / "skills/hormozi/knowledge"
CHANNEL = {"main": "Alex Hormozi", "coaching": "MoreMozi (his coaching calls)", "acq": "Acquisition.com", "guest": "guest interview"}
TIER = {"main": 2, "guest": 3, "acq": 3, "coaching": 4}
MIN_SIM = 0.45          # below this, the claim matches nothing in its source: dropped
REPOINT_MARGIN = 0.06   # best chunk must beat the cited one by this much to replace it

def ts_url(url): return url  # chunk URLs already carry &t=<seconds>s

def gate_pointers(model, claims, keys, ctx, get, put, stats):
    if not claims: return []
    V = np.vstack(list(model.passage_embed([c[:2000] for c in ctx])))
    Q = np.vstack(list(model.query_embed([c["text"] for c in claims])))
    S = Q @ V.T; kept = []
    for ci, c in enumerate(claims):
        cited = [k for k in get(c) if k in keys]
        order = list(np.argsort(-S[ci])); best = order[0]
        if S[ci][best] < MIN_SIM: stats["dropped_nomatch"] += 1; continue
        if not cited: put(c, [keys[best]]); stats["repointed"] += 1; kept.append(c); continue
        ci_idx = [keys.index(k) for k in cited]
        if min(order.index(i) for i in ci_idx) < 3: stats["ok"] += 1
        elif any(abs(best - i) == 1 for i in ci_idx): put(c, sorted({*cited, keys[best]}, key=keys.index)); stats["widened"] += 1
        elif S[ci][best] - max(S[ci][i] for i in ci_idx) > REPOINT_MARGIN: put(c, [keys[best]]); stats["repointed"] += 1
        else: stats["kept_weak"] += 1
        kept.append(c)
    return kept

def copy_ok(text, grams, stats):
    if D.longest_copy(text, grams) >= 8: stats["dropped_copy"] += 1; return False
    return True

def grams6(s):
    w = D.words(s); return {" ".join(w[i:i + 6]) for i in range(len(w) - 5)}

def clean_fw(fws, slugs):
    known = [f for f in fws or [] if f in slugs]
    new = [f for f in fws or [] if isinstance(f, str) and f.startswith("new:")]
    return known, new

def videos(run, model, slugs, st, newnames):
    um = {u["id"]: u for u in D.video_units()}
    claims, cases, vids = [], [], collections.OrderedDict()
    for f in sorted(run.glob("*.json")):
        r = json.loads(f.read_text()); u = um.get(r["unit"])
        if not u: continue
        out = r["out"]; grams = grams6(u["text"]); keys = u["labels"]
        ctx = [re.sub(r"^\[[\d:]+\] ", "", x) for x in u["text"].split("\n\n")]
        cl = [c for c in out.get("claims", []) if c.get("text") and copy_ok(c["text"], grams, st)]
        cl = gate_pointers(model, cl, keys, ctx, lambda c: c.get("t") or [], lambda c, v: c.__setitem__("t", v), st)
        base = {"src": u["kind"], "tier": TIER[u["kind"]], "title": u["title"], "channel": CHANNEL[u["kind"]], "date": u["date"], "video": u["video_id"]}
        for n, c in enumerate(cl, 1):
            fw, new = clean_fw(c.get("frameworks"), slugs); newnames.update(new)
            claims.append({"id": f"{u['id']}#{n}", "text": c["text"].strip(), "type": c.get("type", ""), "frameworks": fw, **base,
                           "at": c["t"][0], "url": u["urls"][c["t"][0]], **({"also_at": c["t"][1:]} if len(c["t"]) > 1 else {})})
        for n, c in enumerate(out.get("cases", []), 1):
            txt = " ".join([c.get("question", ""), c.get("diagnosis", "")] + list(c.get("advice", [])))
            if not copy_ok(txt, grams, st) or not c.get("t"): continue
            cases.append({"id": f"{u['id']}#case{n}", "business": c.get("business", ""), "numbers": c.get("numbers", ""), "question": c.get("question", ""),
                          "diagnosis": c.get("diagnosis", ""), "advice": c.get("advice", []), **base, "at": c["t"][0], "until": c["t"][-1], "url": u["urls"][c["t"][0]]})
        v = vids.setdefault(u["video_id"], {"video": u["video_id"], "title": u["title"], "channel": CHANNEL[u["kind"]], "src": u["kind"], "date": u["date"],
                                             "url": f"https://www.youtube.com/watch?v={u['video_id']}", "summary": "", "segments": []})
        if copy_ok(out.get("summary", ""), grams, st): v["summary"] = (v["summary"] + " " + out.get("summary", "")).strip()
        for s in out.get("segments", []):
            if s.get("topic") and copy_ok(s["topic"], grams, st):
                v["segments"].append({"at": s["t"], "topic": s["topic"], "tags": s.get("tags", [])[:5]})
    return claims, cases, list(vids.values())

def books(run, model, slugs, st, newnames):
    um = {u["id"]: u for u in D.book_units()}
    claims, bmap = [], collections.OrderedDict()
    for f in sorted(run.glob("*.json")):
        r = json.loads(f.read_text()); u = um.get(r["unit"])
        if not u: continue
        out = r["out"]; keys = list(u["pages"]); ctx = list(u["pages"].values())
        # headings are titles and may be reproduced (e.g. "Seven Steps To Creating an Effective Lead Magnet, step 1: …")
        heads = " ".join(s.get("heading", "") for s in out.get("sections", [])) + " " + " ".join(c.get("section", "") for c in out.get("claims", []))
        grams = grams6(u["text"]) - grams6(heads)
        cl = [c for c in out.get("claims", []) if c.get("text") and copy_ok(c["text"], grams, st)]
        cl = gate_pointers(model, cl, keys, ctx, lambda c: [c["page"]] if c.get("page") else [], lambda c, v: c.__setitem__("page", v[0]), st)
        for n, c in enumerate(cl, 1):
            fw, new = clean_fw(c.get("frameworks"), slugs); newnames.update(new)
            claims.append({"id": f"{u['id']}#{n}", "text": c["text"].strip(), "type": c.get("type", ""), "frameworks": fw, "src": "book", "tier": 1,
                           "book": u["book"], "page": c["page"], "section": c.get("section", "")})
        b = bmap.setdefault(u["slug"], {"book": u["book"], "slug": u["slug"], "sections": []})
        for s in out.get("sections", []):
            if s.get("heading") and copy_ok(s.get("topic", ""), grams, st):
                b["sections"].append({"page": s["page"], "heading": s["heading"].strip(), "topic": s.get("topic", "")})
    return claims, list(bmap.values())

def dump(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)); print(f"  {path.relative_to(ROOT)}: {len(rows)} rows, {path.stat().st_size/1e6:.1f} MB")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--videos", default="build/distill/videos"); ap.add_argument("--books", default="build/distill/books")
    a = ap.parse_args()
    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    slugs = {f.stem for f in (ROOT / "skills/hormozi/frameworks").glob("*.md")}
    K.mkdir(exist_ok=True); st = collections.Counter(); newnames = collections.Counter()
    bc, bm = books(ROOT / a.books, model, slugs, st, newnames)
    vc, cases, vm = videos(ROOT / a.videos, model, slugs, st, newnames)
    dump(K / "claims.jsonl", bc + vc); dump(K / "cases.jsonl", cases); dump(K / "videos.jsonl", vm); dump(K / "books.jsonl", bm)
    (ROOT / "build/new-frameworks.json").write_text(json.dumps(newnames.most_common(), indent=0))
    print("  gates:", dict(st))
