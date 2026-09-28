#!/usr/bin/env python3
"""Distill the private library into a shareable knowledge layer: paraphrased claims, cases, video maps
and book section maps, each pointing to an exact timestamp or page. Needs the private index + sources.

  distill.py units video|book                      count the work units
  distill.py run video|book --backend B --run NAME [--jobs 6] [--sample N] [--only id,id] [--kinds main,coaching]
  distill.py check --run NAME                      copy check + pointer check + stats for a run
  distill.py show --run NAME UNIT                  print one unit's output

Backends: agy:<model>  (Antigravity CLI, e.g. agy:gemini-3.8-flash-high)
          codex:<model>:<effort>  (e.g. codex:gpt-6-astra:medium)
Outputs:  build/distill/<run>/<unit>.json   (git-ignored; resumable: finished units are skipped)
"""
import argparse, concurrent.futures as cf, json, os, pathlib, random, re, sqlite3, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "build/distill"
PART = 60  # chunks (~90 min of video) per unit

KIND_NOTE = {"main": "his own channel: solo talks, his podcast, some Q&A", "coaching": "MoreMozi, a channel re-uploading his coaching calls and Q&A answers",
             "acq": "the Acquisition.com company channel", "guest": "a guest appearance on someone else's show: the host also speaks"}
SRC_KIND = {"Alex Hormozi (YouTube)": "main", "MoreMozi (YouTube)": "coaching", "Acquisition.com (YouTube)": "acq", "Guest interview": "guest"}
BOOKS = {"100M-Offers": "$100M Offers", "100M-Leads": "$100M Leads", "100M-Money-Models": "$100M Money Models",
         "100M-Offers-Lost-Chapter": "$100M Offers — The Lost Chapter", "100M-Leads-Bonus-Chapters": "$100M Leads — Bonus Chapters"}

def book_name(slug): return BOOKS.get(slug, "$100M " + slug.removeprefix("100M-").replace("-", " "))

def frameworks_list():
    out = []
    for f in sorted((ROOT / "skills/hormozi/frameworks").glob("*.md")):
        out.append(f"{f.stem} — {f.read_text().splitlines()[0][2:]}")
    return "\n".join(out)

def secs(label):
    p = [int(x) for x in label.split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]

def video_units():
    db = sqlite3.connect(ROOT / "index/hormozi.db")
    groups = {}
    for i, src, title, date, url, body in db.execute("SELECT id, source, title, date, url, body FROM meta WHERE tier BETWEEN 2 AND 4"):
        m = re.search(r"v=([^&]+)", url); t = re.search(r" @ ([\d:]+)$", title)
        if not (m and t): continue
        g = groups.setdefault((SRC_KIND[src], m.group(1)), {"title": title[: t.start()], "date": date, "source": src, "chunks": []})
        g["chunks"].append((secs(t.group(1)), t.group(1), url, body, i))
    units = []
    for (kind, vid), g in sorted(groups.items()):
        ch = sorted(g["chunks"])
        parts = [ch[k:k + PART] for k in range(0, len(ch), PART)]
        for n, part in enumerate(parts, 1):
            uid = f"{kind}-{vid}" + (f"-p{n}" if len(parts) > 1 else "")
            units.append({"id": uid, "layer": "video", "kind": kind, "video_id": vid, "title": g["title"], "date": g["date"],
                          "source": g["source"], "part": f"{n}/{len(parts)}", "labels": [c[1] for c in part],
                          "urls": {c[1]: c[2] for c in part}, "chunk_ids": {c[1]: c[4] for c in part},
                          "text": "\n\n".join(f"[{c[1]}] {c[3]}" for c in part)})
    return units

def book_units():
    units = []
    for f in sorted((ROOT / "sources/books/paged").glob("*.md")):
        pages = [(int(m.group(1)), m.group(2).strip()) for m in re.finditer(r"=== p\. (\d+) ===\n(.*?)(?=\n=== p\. |\Z)", f.read_text(), re.S)]
        buf = []
        for k, (n, txt) in enumerate(pages):
            txt = re.sub(r"Copyright © \d{4} by ACQUISITION\.COM LLC NOT FOR DISTRIBUTION", " ", txt)
            buf.append((n, txt))
            if sum(len(t.split()) for _, t in buf) >= 2400 or k == len(pages) - 1:
                s, e = buf[0][0], buf[-1][0]
                units.append({"id": f"book-{f.stem}-p{s:03d}", "layer": "book", "slug": f.stem, "book": book_name(f.stem), "start": s, "end": e,
                              "pages": {n: t for n, t in buf}, "text": "\n".join(f"=== p. {n} ===\n{t}" for n, t in buf)})
                buf = []
    return units

def units_for(layer): return video_units() if layer == "video" else book_units()

def prompt_for(u, fw):
    tpl = (HERE / "prompts" / f"{u['layer']}.md").read_text()
    if u["layer"] == "video":
        title = u["title"] + (f" (part {u['part']})" if u["part"] != "1/1" else "")
        return tpl.format(title=title, source=u["source"], kind_note=KIND_NOTE[u["kind"]], date=u["date"] or "unknown", text=u["text"], frameworks=fw)
    return tpl.format(book=u["book"], start=u["start"], end=u["end"], text=u["text"], frameworks=fw)

def parse_json(s):
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    a, b = s.find("{"), s.rfind("}")
    return json.loads(s[a:b + 1])

def call(backend, prompt, workdir):
    kind, _, rest = backend.partition(":")
    if kind == "agy":
        r = subprocess.run(["agy", "-p", prompt, "--model", rest, "--output-format", "json", "--print-timeout", "1200s"],
                           cwd=workdir, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1500)
        d = json.loads(r.stdout)
        if d.get("status") != "SUCCESS": raise RuntimeError(f"agy status {d.get('status')}: {r.stderr[-300:]}")
        return d["response"], d.get("usage", {})
    if kind == "codex":
        model, _, effort = rest.partition(":")
        of = workdir / f"codex-{os.getpid()}-{time.time_ns()}.txt"
        r = subprocess.run(["codex", "exec", "--skip-git-repo-check", "-s", "read-only", "-m", model, "-c", f"model_reasoning_effort={effort or 'medium'}",
                            "-o", str(of), "-"], input=prompt, cwd=workdir, capture_output=True, text=True, timeout=1500)
        if not of.exists(): raise RuntimeError(f"codex rc={r.returncode}: {r.stderr[-300:]}")
        txt = of.read_text(); of.unlink()
        m = re.search(r"tokens used\s*\n?\s*([\d,]+)", r.stderr + r.stdout)
        return txt, {"total_tokens": int(m.group(1).replace(",", "")) if m else None}
    if kind == "gemini-api":   # Google AI Studio key (GEMINI_API_KEY), no agent overhead; JSON mode
        import urllib.request
        key = os.environ.get("GEMINI_API_KEY") or subprocess.run(["llm-key", "get", "GEMINI_API_KEY"], capture_output=True, text=True).stdout.strip()
        body = json.dumps({"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                           "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3}}).encode()
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{rest}:generateContent", data=body,
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        with urllib.request.urlopen(req, timeout=600) as r: d = json.loads(r.read())
        return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"] if not p.get("thought")), d.get("usageMetadata", {})
    raise SystemExit(f"unknown backend {backend}")

def norm_label(t): return str(t).strip().strip("[]").strip()

def normalize(u, out):
    """Keep only pointers that exist in the unit; record what was dropped."""
    issues = []
    if u["layer"] == "video":
        labels = set(u["labels"])
        for c in out.get("claims", []):
            ts = [norm_label(t) for t in (c.get("t") or [])]
            c["t"] = [t for t in ts if t in labels]
            if len(c["t"]) < len(ts): issues.append("bad-claim-label")
        for c in out.get("cases", []):
            c["t"] = [t for t in (norm_label(t) for t in (c.get("t") or [])) if t in labels]
        segs = {norm_label(s.get("t")): s for s in out.get("segments", [])}
        missing = [l for l in u["labels"] if l not in segs]
        if missing: issues.append(f"segments-missing:{len(missing)}")
        out["segments"] = [dict(segs[l], t=l) for l in u["labels"] if l in segs]
    else:
        for c in out.get("claims", []):
            try: c["page"] = int(c.get("page"))
            except (TypeError, ValueError): c["page"] = None
            if c["page"] is None or not (u["start"] <= c["page"] <= u["end"]): issues.append("bad-page"); c["page"] = None
    return out, issues

def run(a):
    units = units_for(a.layer)
    if a.kinds: units = [u for u in units if u.get("kind") in a.kinds.split(",") or u.get("slug") in a.kinds.split(",")]
    if a.only: units = [u for u in units if u["id"] in set(a.only.split(","))]
    if a.sample: random.Random(7).shuffle(units); units = units[: a.sample]
    d = OUT / a.run; d.mkdir(parents=True, exist_ok=True); work = OUT / "_work"; work.mkdir(exist_ok=True)
    todo = [u for u in units if not (d / f"{u['id']}.json").exists()]
    if a.reverse: todo.reverse()
    print(f"{a.run}: {len(units)} units, {len(todo)} to do, backend {a.backend}, jobs {a.jobs}", flush=True)
    fw = frameworks_list()
    def claim(u):
        """Several workers (different CLIs, different tabs) share one run dir: a unit is taken by creating its .lock."""
        if (d / f"{u['id']}.json").exists(): return False
        lk = d / f"{u['id']}.lock"
        try: os.close(os.open(lk, os.O_CREAT | os.O_EXCL)); return True
        except FileExistsError:
            if time.time() - lk.stat().st_mtime > 1800: lk.unlink(missing_ok=True); return claim(u)   # stale lock from a killed worker
            return False
    def one(u):
        if not claim(u): return u["id"], "skip (other worker)", 0, 0
        p = prompt_for(u, fw); t0 = time.time(); last = None
        try:
            for attempt in range(3):
                try:
                    txt, usage = call(a.backend, p, work)
                    out, issues = normalize(u, parse_json(txt))
                    rec = {"unit": u["id"], "backend": a.backend, "elapsed": round(time.time() - t0, 1), "usage": usage, "issues": issues, "out": out}
                    (d / f"{u['id']}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
                    (d / f"{u['id']}.err").unlink(missing_ok=True)
                    return u["id"], "ok", rec["elapsed"], len(out.get("claims", []))
                except Exception as e:
                    last = f"{type(e).__name__}: {str(e)[:300]}"; time.sleep(5 + (60 if "429" in last or "quota" in last.lower() else 20) * attempt)
            (d / f"{u['id']}.err").write_text(last or "?")
            return u["id"], "ERR " + (last or ""), round(time.time() - t0, 1), 0
        finally:
            (d / f"{u['id']}.lock").unlink(missing_ok=True)
    done = 0
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for uid, st, el, nc in ex.map(one, todo):
            done += 1
            if not st.startswith("skip"): print(f"[{done}/{len(todo)}] {uid} {st} {el}s claims={nc}", flush=True)

def unit_map(layer): return {u["id"]: u for u in units_for(layer)}

def words(s): return re.findall(r"[a-z0-9']+", s.lower().replace("’", "'"))

def longest_copy(text, src_grams, n=6):
    """Longest run of consecutive source words reproduced in text (runs shorter than n are ignored)."""
    w = words(text); best = 0; i = 0
    while i + n <= len(w):
        if " ".join(w[i:i + n]) in src_grams:
            j = i + n
            while j < len(w) and " ".join(w[j - n + 1:j + 1]) in src_grams: j += 1
            best = max(best, j - i); i = j
        else: i += 1
    return best

def texts_of(out):
    for c in out.get("claims", []): yield "claim", c.get("text", ""), c
    for c in out.get("cases", []): yield "case", " ".join([c.get("question", ""), c.get("diagnosis", "")] + list(c.get("advice", []))), c
    for s in out.get("segments", []): yield "segment", s.get("topic", ""), s
    for s in out.get("sections", []): yield "section-topic", s.get("topic", ""), s
    yield "summary", out.get("summary", ""), None

def check(a):
    d = OUT / a.run; recs = [json.loads(f.read_text()) for f in sorted(d.glob("*.json"))]
    if not recs: sys.exit("no outputs")
    layer = "book" if recs[0]["unit"].startswith("book-") else "video"
    um = unit_map(layer)
    import numpy as np
    from fastembed import TextEmbedding
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    n6 = lambda s: {" ".join(w[i:i + 6]) for w in [words(s)] for i in range(len(w) - 5)}
    st = {"units": 0, "claims": 0, "cases": 0, "copy8": 0, "copy6": 0, "ptr_ok": 0, "ptr_n": 0, "no_ptr": 0, "minutes": 0, "elapsed": 0, "tokens": 0, "issues": 0}
    flags = []
    for r in recs:
        u = um[r["unit"]]; out = r["out"]; st["units"] += 1; st["elapsed"] += r["elapsed"]; st["tokens"] += (r["usage"] or {}).get("total_tokens") or 0
        st["issues"] += bool(r["issues"])
        grams = n6(u["text"])
        for kind, t, obj in texts_of(out):
            k = longest_copy(t, grams)
            if k >= 8: st["copy8"] += 1; flags.append((r["unit"], kind, k, t))
            elif k >= 6: st["copy6"] += 1
        claims = out.get("claims", []); st["claims"] += len(claims); st["cases"] += len(out.get("cases", []))
        if layer == "video":
            st["minutes"] += len(u["labels"]) * 1.5
            keys = u["labels"]; ctx = [re.sub(r"^\[[\d:]+\] ", "", x) for x in u["text"].split("\n\n")]
        else:
            st["minutes"] += len(u["pages"])
            keys = list(u["pages"]); ctx = list(u["pages"].values())
        if not claims: continue
        V = np.vstack(list(model.passage_embed([c[:2000] for c in ctx])))
        Q = np.vstack(list(model.query_embed([c.get("text", "") for c in claims])))
        S = Q @ V.T
        for ci, c in enumerate(claims):
            cited = c.get("t") if layer == "video" else ([c["page"]] if c.get("page") else [])
            if not cited: st["no_ptr"] += 1; continue
            order = list(np.argsort(-S[ci]))
            rank = min(order.index(keys.index(x)) for x in cited if x in keys)
            st["ptr_n"] += 1; st["ptr_ok"] += rank < 3
    per = "min of video" if layer == "video" else "pages"
    print(f"run {a.run}  ({recs[0]['backend']})")
    print(f"  units {st['units']}  claims {st['claims']} ({st['claims']/max(1,st['minutes']):.2f} per {per.split()[0]})  cases {st['cases']}")
    print(f"  pointer in top-3 of its unit: {st['ptr_ok']}/{st['ptr_n']} ({st['ptr_ok']/max(1,st['ptr_n']):.0%})  claims w/o pointer {st['no_ptr']}")
    print(f"  copy runs >=8 words: {st['copy8']}   6-7 words: {st['copy6']}   units with issues: {st['issues']}")
    print(f"  avg {st['elapsed']/st['units']:.0f}s/unit  tokens {st['tokens']:,}")
    for f in flags[: a.show]: print(f"  COPY {f[0]} {f[1]} {f[2]}w: {f[3][:160]}")

def show(a):
    r = json.loads((OUT / a.run / f"{a.unit}.json").read_text()); print(json.dumps(r["out"], indent=1, ensure_ascii=False))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("units"); x.add_argument("layer", choices=["video", "book"])
    x = sub.add_parser("run"); x.add_argument("layer", choices=["video", "book"]); x.add_argument("--backend", required=True); x.add_argument("--run", required=True)
    x.add_argument("--jobs", type=int, default=6); x.add_argument("--sample", type=int); x.add_argument("--only"); x.add_argument("--kinds")
    x.add_argument("--reverse", action="store_true", help="work from the end of the queue (second worker on the same run)")
    x = sub.add_parser("check"); x.add_argument("--run", required=True); x.add_argument("--show", type=int, default=8)
    x = sub.add_parser("show"); x.add_argument("--run", required=True); x.add_argument("unit")
    a = ap.parse_args()
    if a.cmd == "units":
        us = units_for(a.layer); print(len(us), "units;", sum(len(u["text"].split()) for u in us), "words")
        if a.layer == "video":
            from collections import Counter; print(Counter(u["kind"] for u in us))
    elif a.cmd == "run": run(a)
    elif a.cmd == "check": check(a)
    else: show(a)
