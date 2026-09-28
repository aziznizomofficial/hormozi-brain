# Hormozi Brain

Ask any business question and get the answer Alex Hormozi would give — in his blunt, numbers-first style, in your language — with the **book page or video second** it comes from.

Works in **Claude Code, Codex, Gemini CLI, Antigravity, Cursor and OpenCode**, and as an upload for **ChatGPT, claude.ai, Gemini Gems and NotebookLM**. No API keys, no server, nothing to pay for. Needs only Python 3.9+.

> Unofficial fan-made study tool. Not affiliated with or endorsed by Alex Hormozi or Acquisition.com. It contains **no text from his books or videos**: only short paraphrased entries that point to the originals. See [NOTICE.md](NOTICE.md).

## What's inside

A paraphrased, source-pointed map of his work:

| | Entries | Points to |
|---|---|---|
| Framework cards | {{CARDS}} named models: steps, math, mistakes | book pages + video timestamps |
| Book & playbook ideas | {{BOOK_CLAIMS}} from 16 titles | book, page, section heading |
| Video ideas | {{VIDEO_CLAIMS}} from {{VIDEOS}} videos: his channel, guest interviews, Acquisition.com, coaching calls | YouTube link at the exact second |
| Real business cases | {{CASES}}: the numbers, his diagnosis, his fix | YouTube link at the exact second |
| Video maps | a topic line for every ~90 seconds of every video | YouTube link |

## Install

**Claude Code** (plugin):
```
/plugin marketplace add aziznizomofficial/hormozi-brain
/plugin install hormozi-brain@hormozi-brain
```

**Codex, Gemini CLI, Antigravity, Cursor, OpenCode — or Claude Code without the plugin** (macOS, Linux, Windows via WSL):
```bash
git clone https://github.com/aziznizomofficial/hormozi-brain.git
cd hormozi-brain && ./install.sh              # add --semantic for meaning-based search (optional, ~200 MB)
```
The installer links the skills into every agent it finds and puts a `hormozi` command on your PATH. `./install.sh --uninstall` removes everything.

**ChatGPT, claude.ai, Gemini, NotebookLM** (no install): download `hormozi-chat-pack.zip` from [Releases](https://github.com/aziznizomofficial/hormozi-brain/releases), upload the files to a Project / GPT / Gem / notebook, and paste `INSTRUCTIONS.md` into its instructions. claude.ai users with code execution can instead upload `hormozi-skill.zip` under Settings → Capabilities → Skills.

## Use

| Ask | Does |
|---|---|
| `/hormozi <question>` | Answers in his voice, cites pages and timestamps |
| `/hormozi-diagnose` | Full business audit: intake, the one constraint, 7/30/90-day plan with the math |
| `/hormozi-offer` | Builds a Grand Slam Offer step by step |
| `/hormozi-review` | Scores and rewrites an ad, hook, offer, script or landing page |

Ask in any language; answers come back in yours (framework names stay in English). In Claude Code there is also a `hormozi` subagent for whole audits.

The CLI works on its own too:
```bash
hormozi search "how do I raise prices without losing customers"
hormozi search "gym with high churn" --kind case
hormozi frameworks value-equation
hormozi get <id>            # an entry plus what surrounds it
hormozi verify <id>         # the original words: live YouTube captions, or your own PDF of the book
```

## How it was built, and how good it is

The maintainer distilled his own copies of the books and ~2,000 videos' captions into short paraphrased entries (books with Codex; videos with Gemini Flash and Codex; Claude orchestrating and reviewing). Two automated gates run on everything that ships: entries that repeat 8+ consecutive words of the source are dropped, and every pointer is checked against the passage it cites. Details in [ARCHITECTURE.md](ARCHITECTURE.md).

Benchmark: 30 real business questions (`evals/`), top 8 results each.

| | On-topic results | Questions well covered | Has a book page | Citation leads to on-topic original |
|---|---|---|---|---|
{{BENCH}}

## Limits

- Entries are machine-assisted paraphrases and can be wrong or miss nuance. Check the original (`hormozi verify <id>`) before relying on a detail.
- Page numbers refer to the PDF editions; section headings let you find the spot in any edition.
- The map is English. Questions in other languages work because the skills translate them into English search terms first.

## Maintainers

Rebuilding the map needs your own copies of the sources; see [ARCHITECTURE.md](ARCHITECTURE.md). Code is MIT ([LICENSE](LICENSE)).
