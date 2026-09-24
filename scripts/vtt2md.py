#!/usr/bin/env python3
"""Convert yt-dlp auto-caption VTT + info.json into timestamped Markdown transcripts."""
import json, re, sys, pathlib
src = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
TS = re.compile(r"(\d+):(\d+):(\d+)\.\d+ -->")
def secs(m): return int(m[1])*3600+int(m[2])*60+int(m[3])
n = 0
for vtt in sorted(src.glob("*.vtt")):
    stem = vtt.name.split(".")[0]                      # 20260911_ID
    info_p = src / f"{stem}.info.json"
    info = json.loads(info_p.read_text()) if info_p.exists() else {}
    vid = info.get("id", stem.split("_",1)[1]); url = f"https://www.youtube.com/watch?v={vid}"
    words, t, last = [], 0, None
    chunks = {}
    for line in vtt.read_text(errors="ignore").splitlines():
        m = TS.match(line)
        if m: t = secs(m); continue
        if not line.strip() or line.startswith(("WEBVTT","Kind:","Language:")) or "-->" in line: continue
        if "<c>" not in line and "<" not in line:      # rolling duplicate lines: skip plain repeats
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean != last:
            chunks.setdefault(t//90*90, []).append(clean); last = clean
    if not chunks:                                     # manual subs have no <c> tags
        for line in vtt.read_text(errors="ignore").splitlines():
            m = TS.match(line)
            if m: t = secs(m); continue
            if line.strip() and "-->" not in line and not line.startswith(("WEBVTT","Kind:","Language:")):
                clean = re.sub(r"<[^>]+>", "", line).strip()
                if clean != last: chunks.setdefault(t//90*90, []).append(clean); last = clean
    d = info.get("upload_date", stem[:8]); date = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    title = info.get("title", vid).replace('"', "'")
    body = [f'---\nepisode_id: "{vid}"\ntitle: "{title}"\npublished: "{date}"\nduration_seconds: {info.get("duration",0)}\nepisode_url: "{url}"\nchannel: "Alex Hormozi"\ntranscript_source: "automatic_captions"\n---\n\n# {title}\n\nVideo: {url}\n']
    for s in sorted(chunks):
        body.append(f"\n## [{s//60:02d}:{s%60:02d}]({url}&t={s}s)\n\n" + " ".join(chunks[s]) + "\n")
    (out / f"{vid}.md").write_text("".join(body)); n += 1
print(f"converted {n}")
