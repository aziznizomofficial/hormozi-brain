# Hormozi Brain — architecture

Goal: the most accurate, best-sourced Hormozi advisor for Claude Code and Codex. "Best" is measured, not claimed: a fixed benchmark (`evals/`) scores every build against the strongest public repo.

## Decisions that differ from the obvious plan

1. **Retrieval + a framework layer, not fine-tuning.** Fine-tuning blurs sources and invents quotes. Every answer here is traceable to a page or a video second.
2. **Rank sources by authority.** Books define frameworks; videos show how he applies them. A book page beats a 90-second clip for "what is X"; a coaching call beats a book for "what would he do with MY business".
3. **Primary sources only.** No third-party summaries (they drift from what he said), no leaked paid courses (piracy, and one takedown kills the repo). Free Acquisition.com course notes are kept but tagged as secondary.
4. **CLI + skills, no MCP server.** An MCP server loads tool schemas into every session; this machine already had context-bloat problems. A CLI costs zero tokens until used and works identically in Claude Code and Codex.
5. **Code public-able, corpus never.** The repo holds the engine, skills, voice data and evals. `sources/` and `index/` are rebuilt locally from each user's own copies. That is what makes it shareable later without legal risk.
6. **Voice from measurement.** The voice guide is derived from frequency analysis of his speech, not vibes; catchphrases are rationed because the data shows he rarely uses them.
7. **Answer in the user's language.** Uzbek and Russian answers with English framework names — a moat no public repo has, and directly usable for Strateg AI clients.

## Layers

| Layer | What | Where |
|---|---|---|
| Sources | books, playbooks, YouTube (main, MoreMozi, Acquisition.com, guest interviews), free courses | `sources/` (git-ignored) |
| Normalize | one Markdown/text format with metadata: source tier, date, URL+timestamp or book+page | `scripts/vtt2md.py`, `scripts/build_index.py` |
| Dedupe | MoreMozi re-uploads clips of long videos; near-duplicate chunks collapse to the earliest/longest | `build_index.py` |
| Index | SQLite FTS5 (BM25) + local embeddings, fused by reciprocal rank, weighted by tier | `index/` (git-ignored) |
| Frameworks | ~80 framework cards: paraphrased definition, steps, when to use, common mistakes, source refs | `frameworks/` |
| Voice | measured speech patterns + rationed signature lines | `skill/references/voice.md` |
| Interface | `hormozi` CLI; skills `/hormozi`, `/hormozi-diagnose`, `/hormozi-offer`, `/hormozi-review`; Claude subagent; Codex skills via symlink | `skills/`, `agents/` |
| Evals | 40 real business questions, graded on groundedness, framework accuracy, actionability, voice | `evals/` |

## Source tiers

| Tier | Source | Used for |
|---|---|---|
| 1 | Books and $100M playbooks (your copies) | canonical definitions, page refs |
| 2 | @AlexHormozi long-form videos | his own explanations, stories |
| 3 | Guest interviews, Acquisition.com channel | unscripted voice, personal history |
| 4 | MoreMozi coaching calls | applying frameworks to real businesses |
| 5 | Free-course notes (third-party written) | routing only, never quoted |

## Copyright guardrails

Answers paraphrase, quote at most one short line per source, and always link the source. Nothing in `sources/` or `index/` is ever committed or published.
