#!/usr/bin/env python3
"""Build the chat pack: the same knowledge as Markdown files for AIs that can't run a CLI
(ChatGPT Projects / custom GPTs, claude.ai Projects, Gemini Gems, NotebookLM). Also zips the skill for claude.ai.

  scripts/chatpack.py            → dist/hormozi-chat-pack.zip, dist/hormozi-skill.zip
"""
import collections, json, pathlib, re, shutil, zipfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
SK = ROOT / "skills/hormozi"; OUT = ROOT / "dist/chat-pack"
rows = lambda n: [json.loads(l) for l in (SK / "knowledge" / n).open(encoding="utf-8")]

def label(at):
    p = [int(x) for x in at.split(":")]; s = p[-1] + 60 * p[-2] + (3600 * p[-3] if len(p) == 3 else 0)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"

INSTRUCTIONS = """# Hormozi Brain — instructions (paste into your Project / GPT / Gem instructions)

You are an unofficial advisor that thinks and talks like Alex Hormozi, grounded ONLY in the attached files. Never claim to be him. Not affiliated with Alex Hormozi or Acquisition.com.

The attached files are a paraphrased map of his work. Every line points to the original: a book page + section, or a YouTube link with a timestamp.
- frameworks.md: his named models (steps, math, mistakes, page refs). Read the matching card first.
- book-claims.md: ideas from his books and playbooks by book and page (most authoritative).
- video-claims-*.md: ideas from his videos, interviews and coaching calls, with timestamped links.
- cases.md: real businesses he advised: their numbers, his diagnosis, his fix.

Method:
1. Map the question to 1–3 frameworks and read those cards.
2. Look up the definition in book-claims.md, then how he applies it (cases.md, video-claims). Search the files with English terms, whatever language the user writes in.
3. If you lack the business facts, first ask ONE short list: offer and price, customers and revenue per month, gross margin, CAC, LTV/churn, lead sources, close rate.
4. Name the ONE constraint, give the move, prove it with arithmetic on their numbers.
5. Cite 2–5 sources at the end, copied from the files: "$100M Offers, p. 64 (section)" or "[video title @ mm:ss](link)". Entries are paraphrases: never present them as his exact words.
6. If the files have nothing on it, say so and label your reasoning as inference, not his view.

Voice:
{voice}

Answer in the user's language; keep framework names in English.
"""

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    voice = (SK / "references/voice.md").read_text(encoding="utf-8").split("\n", 1)[1]
    (OUT / "INSTRUCTIONS.md").write_text(INSTRUCTIONS.format(voice=voice.strip()), encoding="utf-8")
    cards = sorted((SK / "frameworks").glob("*.md"))
    (OUT / "frameworks.md").write_text("# Framework cards\n\n" + "\n\n---\n\n".join(f.read_text(encoding="utf-8").strip() for f in cards) + "\n", encoding="utf-8")
    claims = rows("claims.jsonl")
    books = collections.defaultdict(list)
    for c in claims:
        if c["src"] == "book": books[c["book"]].append(c)
    with (OUT / "book-claims.md").open("w", encoding="utf-8") as f:
        f.write("# Book and playbook claims (paraphrased; page = PDF page, section = heading)\n")
        for b, cs in books.items():
            f.write(f"\n## {b}\n")
            for c in sorted(cs, key=lambda c: c["page"]): f.write(f"- p. {c['page']}{' (' + c['section'] + ')' if c['section'] else ''}: {c['text']}\n")
    vids = collections.OrderedDict()
    for c in claims:
        if c["src"] != "book": vids.setdefault((c["src"], c["video"]), []).append(c)
    groups = {"main": "his-channel", "guest": "interviews", "acq": "interviews", "coaching": "coaching-calls"}
    files = collections.defaultdict(list)
    for (src, vid), cs in vids.items():
        c0 = cs[0]; block = [f"\n## {c0['title']} ({c0['channel']}, {c0['date']})\nhttps://www.youtube.com/watch?v={vid}\n"]
        block += [f"- [{label(c['at'])}]({c['url']}) {c['text']}\n" for c in cs]
        files[groups[src]].append("".join(block))
    for name, blocks in files.items():
        # keep each file well under chat-app upload limits (~2M tokens): split every ~3 MB
        part, size, n = [], 0, 1
        for b in blocks + [None]:
            if b is None or size > 3_000_000:
                (OUT / f"video-claims-{name}{'-' + str(n) if n > 1 or size > 3_000_000 else ''}.md").write_text(f"# Video claims: {name} (part {n})\n" + "".join(part), encoding="utf-8")
                part, size, n = [], 0, n + 1
            if b: part.append(b); size += len(b)
    with (OUT / "cases.md").open("w", encoding="utf-8") as f:
        f.write("# Cases: real businesses he advised (paraphrased)\n")
        for c in rows("cases.jsonl"):
            f.write(f"\n## {c['business']}\n- numbers: {c['numbers'] or 'n/a'}\n- stuck on: {c['question']}\n- his diagnosis: {c['diagnosis']}\n"
                    f"- his advice: {'; '.join(c['advice'])}\n- source: [{c['title']} @ {label(c['at'])}]({c['url']})\n")
    shutil.copy(ROOT / "NOTICE.md", OUT / "NOTICE.md")
    dist = ROOT / "dist"
    with zipfile.ZipFile(dist / "hormozi-chat-pack.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()): z.write(p, f"hormozi-chat-pack/{p.name}")
    with zipfile.ZipFile(dist / "hormozi-skill.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(SK.rglob("*")):
            if p.is_file() and not re.search(r"/\.(cache|venv)/", str(p)): z.write(p, f"hormozi/{p.relative_to(SK)}")
    for p in sorted(dist.glob("*.zip")) + sorted(OUT.iterdir()): print(f"{p.stat().st_size / 1e6:7.1f} MB  {p.relative_to(ROOT)}")

if __name__ == "__main__": main()
