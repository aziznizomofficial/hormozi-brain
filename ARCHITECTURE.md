# Hormozi Brain — architecture

Goal: the most accurate, best-sourced Hormozi advisor that anyone can install, without shipping a word of his books or transcripts. "Best" is measured, not claimed: `evals/` scores every build on 30 real business questions.

## The core idea: ship a map, not the territory

His books and videos are copyrighted; his ideas, numbers and frameworks are not. So the repo ships a **paraphrased map** in which every entry points to the exact page or video second it came from. Users get the knowledge and the citations; the originals stay with their owners (buy the books, watch the videos, or run `hormozi verify <id>` to fetch the original captions live).

```
private, maintainer's machine only                          public repo
─────────────────────────────────                          ───────────
16 books/playbooks (own copies)  ─┐                         skills/hormozi/knowledge/
~2,000 YouTube caption files     ─┼─► distill ─► gates ─►     claims.jsonl   one idea, ≤ 40 words, + pointer
   his channel, guests,          ─┘   (LLMs)    (copy,        cases.jsonl    real business, numbers, his fix
   Acquisition.com, MoreMozi                   pointer)       videos.jsonl   timestamped topic map per video
                                                              books.jsonl    section headings + pages
                                                            skills/hormozi/frameworks/*.md   named models
```

## Decisions

1. **Retrieval over a paraphrased map, not fine-tuning.** Fine-tuning blurs sources and invents quotes. Every answer here is traceable to a page or a video second.
2. **Idea index, not abridgment.** Book entries are capped at ~1 per page and prioritise definitions, steps and numbers; anecdotes, examples and scripts are described, never retold. A page-by-page retelling of a book is a derivative work; an index of ideas with pointers is not.
3. **Two automated gates on everything shipped** (`scripts/distill/assemble.py`, needs the private originals):
   - *copy gate*: any entry sharing 8+ consecutive words with its source is dropped (framework cards: rewritten).
   - *pointer gate*: each claim is embedded against every chunk/page of its source; a pointer outside the top 3 is widened to the adjacent chunk, re-pointed when another chunk clearly wins, or the claim is dropped when nothing in the source matches it.
4. **Rank sources by authority.** Book page > his own video > interview / Acquisition.com > coaching call. A coaching call beats a book for "what would he do with MY business", so cases are a separate kind.
5. **Right model for each job.** Books (where fidelity matters most) were distilled by Codex (gpt-6-astra); ~2,000 video units by Gemini Flash through the Antigravity CLI, with Codex taking the long interviews; Claude orchestrated, ran the gates and reviewed samples. Pilots compared Gemini Flash, Gemini Pro and Codex on the same units before choosing (Pro was dropped: it invented details).
6. **CLI + skills, no MCP server.** A CLI costs zero tokens until used and works identically in every agent. The CLI needs only Python 3.9 + SQLite FTS5 (keyword search); `hormozi setup --semantic` adds local embeddings.
7. **Self-contained skill folder.** `skills/hormozi/` carries its CLI, knowledge, cards and voice guide (Agent Skills layout), so the same folder works as a Claude Code plugin, in Codex/Gemini/Antigravity/Cursor/OpenCode skill folders, and as a claude.ai upload. Chat-only AIs get `dist/hormozi-chat-pack.zip`.
8. **Voice from measurement.** The voice guide is derived from frequency analysis of 3.7M words of his speech; catchphrases are rationed because the data shows he rarely uses them.
9. **Answer in the user's language, search in English.** The map is English; the skills translate the question into English search terms first.

## Layers

| Layer | What | Where |
|---|---|---|
| Sources (private) | books, playbooks, YouTube captions | `sources/` (git-ignored), `rebuild.sh` |
| Private index | full-text + embeddings over the originals, for distilling and gating | `index/` (git-ignored), `scripts/library.py` |
| Distill | per-video / per-page-run extraction, resumable, lock-coordinated workers | `scripts/distill/distill.py`, `run_all.sh`, `prompts/` |
| Gates + assembly | copy gate, pointer gate, knowledge files | `scripts/distill/assemble.py` |
| Knowledge (public) | claims, cases, video maps, book section maps | `skills/hormozi/knowledge/` |
| Frameworks (public) | named models: definition, steps, when to use, mistakes, math, sources | `skills/hormozi/frameworks/` |
| Interface | `hormozi` CLI; skills `hormozi`, `hormozi-diagnose`, `hormozi-offer`, `hormozi-review`; Claude subagent | `skills/`, `agents/` |
| Packaging | Claude Code plugin + marketplace, `install.sh`, chat pack | `.claude-plugin/`, `install.sh`, `scripts/chatpack.py` |
| Evals | shipped layer vs private library on 30 questions | `evals/knowledge.py`, `evals/retrieval.py` |

## Rebuilding the knowledge layer (maintainer)

```bash
./rebuild.sh                                   # fetch sources, build the private index (needs your own book PDFs)
scripts/distill/run_all.sh books-codex         # any number of workers, any mix of CLIs, in parallel
scripts/distill/run_all.sh videos-gemini
.venv/bin/python scripts/distill/assemble.py   # gates → skills/hormozi/knowledge/*.jsonl
python3 evals/knowledge.py                     # benchmark the shipped layer
python3 scripts/chatpack.py                    # release zips
```
