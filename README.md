# Hormozi Brain

A private Claude Code / Codex skill (`/hormozi`) that answers business questions the way Alex Hormozi would, grounded in a local searchable library of his public material, with timestamped source links. Unofficial; not affiliated with Alex Hormozi or Acquisition.com. For personal use only: do not resell or ship inside client products.

## What is in the library

| Source | How it is fetched |
|---|---|
| MoreMozi YouTube channel, 2,039 transcripts | cloned from github.com/poseljacob/ask-hormozi (MIT) |
| @AlexHormozi YouTube channel, ~554 videos + streams | captions pulled with yt-dlp |
| Free Acquisition.com courses: Offers, Leads, Money Models, Scaling | notes from github.com/Risedial/Alex-Hormozi-Full-Course-Content |
| $100M Journal (free official PDF) | acquisition.com |
| Your own books / playbooks (optional) | drop .md or .txt files into `sources/books/`, then rebuild |

The recurring "free gift / roadmap" promo read is stripped from every transcript before indexing.

## Recovery from GitHub alone

Requires macOS or Linux, python3, git, yt-dlp, pdftotext (poppler).

```bash
git clone https://github.com/<you>/hormozi-brain.git ~/code/hormozi-brain
cd ~/code/hormozi-brain && ./rebuild.sh          # ~40 min, mostly caption downloads
ln -sfn ~/code/hormozi-brain/skill ~/.claude/skills/hormozi
ln -sfn ~/code/hormozi-brain/skill ~/.codex/skills/hormozi
```

`sources/` and `index/` are git-ignored on purpose: they are third-party content and are rebuilt, never committed.

## Use

- In Claude Code: `/hormozi how do I raise prices without losing clients?`
- Direct search: `scripts/hormozi search "price raise" -n 8` (`--source youtube|course|book`), `scripts/hormozi stats`
- Refresh with new videos: `./rebuild.sh`

## Layout

- `skill/SKILL.md` — the skill; `skill/references/voice.md` — his speech patterns, measured on the corpus
- `scripts/vtt2md.py` — captions to timestamped Markdown; `scripts/build_index.py` — SQLite FTS5 index; `scripts/hormozi` — search CLI
