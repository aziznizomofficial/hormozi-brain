# Hormozi Brain

A private advisor for Claude Code and Codex that answers business questions the way Alex Hormozi would. Every answer is grounded in his own books, playbooks, videos and interviews, with page numbers and timestamped links. Unofficial; not affiliated with Alex Hormozi or Acquisition.com. Personal use only.

## What it knows

| Tier | Source | Size |
|---|---|---|
| 1 | His books and $100M playbooks (your own copies) | 16 titles, ~275k words |
| 2 | @AlexHormozi YouTube long-form | 545 videos |
| 3 | Guest interviews (Diary of a CEO, Chris Williamson, My First Million, Tom Bilyeu, Lewis Howes, …) | 49 interviews, ~80 hours |
| 3 | Acquisition.com YouTube | 57 videos |
| 4 | MoreMozi coaching calls | 2,039 videos |
| 5 | Free Acquisition.com course notes (third-party written, routing only) | 4 courses |

Plus **115 framework cards** in `frameworks/`: his models in plain words (steps, when to use, mistakes, math) with exact page references. They are paraphrased and checked automatically for copied text.

Near-duplicate clips are collapsed (6,000 chunks), and his recurring promo read is stripped from all transcripts.

## Skills

| Command | Does |
|---|---|
| `/hormozi <question>` | Answer in his voice with sources |
| `/hormozi-diagnose` | Full business audit: intake, one constraint, 7/30/90-day plan, math, saved report |
| `/hormozi-offer` | Build a Grand Slam Offer step by step |
| `/hormozi-review` | Score and rewrite an ad, hook, offer, script or page |

Also a Claude subagent `hormozi` for delegating whole audits. Answers come in the user's language; framework names stay in English.

## Benchmark

`evals/retrieval.py` runs 30 real business questions through this library and through the corpora other repos ship.

| System | On-topic in top 8 | Questions well covered | Citable book page in top 8 |
|---|---|---|---|
| This repo | 79% | 30/30 | 28/30 |
| MoreMozi-only (viclaranja/hormozi-ai-skill, poseljacob/ask-hormozi) | 63% | 23/30 | 0/30 |
| Course-notes-only repos | 82% | 27/30 | 0/30 |

## Recovery from GitHub alone

Needs macOS/Linux, python3.12, git, yt-dlp, pdftotext (poppler), and rclone if the books come from Google Drive.

```bash
git clone https://github.com/aziznizomofficial/hormozi-brain.git ~/code/hormozi-brain
cd ~/code/hormozi-brain && ./rebuild.sh      # ~1 hour: caption downloads + embeddings
for s in skills/*; do ln -sfn "$PWD/$s" ~/.claude/skills/$(basename $s); ln -sfn "$PWD/$s" ~/.codex/skills/$(basename $s); done
ln -sfn "$PWD/agents/hormozi.md" ~/.claude/agents/hormozi.md
```

Books: by default `rebuild.sh` copies the Drive folder `g1:Books BAZA/English/Alex Hormozi (All Books)`. Set `BOOKS_REMOTE` or put PDFs in `sources/books/drive/` instead. `sources/`, `index/` and `.venv/` are git-ignored on purpose: third-party content is rebuilt locally and never committed.

## CLI

```bash
scripts/hormozi frameworks [slug]                 # list or read framework cards
scripts/hormozi search "question" [-n 8] [--kind book|video|interview|coaching|notes] [--mode keyword]
scripts/hormozi get <id> [--around 1]             # full passage + neighbours
scripts/hormozi stats
```

## Adding material

Drop owned PDFs into `sources/books/drive/` and run `./rebuild.sh`. New framework cards go in `frameworks/`, following the template of any existing card. See `ARCHITECTURE.md` for the design and the decisions behind it.
