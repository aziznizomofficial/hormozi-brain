# Hormozi Brain — instructions for AI agents

This repo is an unofficial Alex Hormozi-style business advisor packaged as Agent Skills. Not affiliated with Alex Hormozi or Acquisition.com.

## Answering a business question "the way Hormozi would"

Follow `skills/hormozi/SKILL.md`. Its CLI needs only Python 3.9+:

```bash
python3 skills/hormozi/scripts/hormozi.py frameworks              # his named models
python3 skills/hormozi/scripts/hormozi.py search "raise prices without losing customers"
python3 skills/hormozi/scripts/hormozi.py get <id>
```

- Full business audit: `skills/hormozi-diagnose/SKILL.md`
- Build an offer: `skills/hormozi-offer/SKILL.md`
- Critique an ad, hook, script or page: `skills/hormozi-review/SKILL.md`
- Voice guide: `skills/hormozi/references/voice.md`

Search in English (the map is English), answer in the user's language, cite the page or timestamp each entry points to.

## Working on the repo itself

- `skills/hormozi/knowledge/*.jsonl` and `skills/hormozi/frameworks/*.md` are generated and gated (see `ARCHITECTURE.md`). Never paste text from Hormozi's books or transcripts into them; every entry must be a paraphrase with a pointer.
- `scripts/`, `rebuild.sh` and `evals/` are the maintainer's pipeline. They need the maintainer's private copies of the sources and are not needed to use the skills.
