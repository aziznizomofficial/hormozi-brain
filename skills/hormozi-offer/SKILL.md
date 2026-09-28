---
name: hormozi-offer
description: Build a Grand Slam Offer with Alex Hormozi's $100M Offers method — dream outcome, problems → solutions, delivery vehicles, value stack, pricing, guarantee, scarcity/urgency, bonuses, naming — grounded in the book with page refs. Use for /hormozi-offer or "make my offer irresistible".
---

# Grand Slam Offer builder

Uses the same map and voice as the `hormozi` skill: read `../hormozi/SKILL.md` and `../hormozi/references/voice.md` (relative to this skill's folder) first. CLI: `h() { python3 "<this skill folder>/../hormozi/scripts/hormozi.py" "$@"; }` (the `hormozi` skill sits next to this one). Before each step, read the matching framework card (`h frameworks <slug>`) and cite its pages.

Steps — show your work at each, and ask the user to confirm or correct before moving on when their input changes the result:
1. **Market check** — is the market starving (pain, purchasing power, easy to target, growing)? Pick the niche.
2. **Dream outcome** — in the buyer's words, with a number and a timeframe.
3. **Problems list** — every obstacle before, during and after, including the fears.
4. **Solutions** — flip each problem into a "how to…" solution.
5. **Delivery vehicles** — for each solution, cost-to-deliver vs value; trim and stack.
6. **Value equation check** — raise dream outcome and likelihood, cut time delay and effort. Score each 1–10.
7. **Pricing** — price on value, not cost; show the price vs value gap.
8. **Enhancers** — scarcity, urgency, bonuses (each with its own value), guarantee type, name (use his naming formula).
9. **Output** — one-page offer: headline name, who it's for, what they get (stack with values), price, guarantee, urgency, plus a 30-second verbal pitch. Save to `~/Documents/Hormozi Reports/offer-<name>-<date>.md`.

Answer in the user's language; keep framework names in English. Always run `h search` in English, whatever language the user writes in.
