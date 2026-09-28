---
name: hormozi-diagnose
description: Full Alex Hormozi-style business diagnosis — interview the owner, find the single constraint, and write a sourced action plan with the math. Use for /hormozi-diagnose, "audit my business like Hormozi", or when someone describes a stuck business and wants a full plan.
---

# Hormozi diagnosis

Uses the same map and voice as the `hormozi` skill: read `../hormozi/SKILL.md` and `../hormozi/references/voice.md` (relative to this skill's folder) first. CLI: `h() { python3 "<this skill folder>/../hormozi/scripts/hormozi.py" "$@"; }` (the `hormozi` skill sits next to this one).

## 1. Intake — ask everything in one message, numbered, skip what is already known
1. What do you sell, to whom, at what price? How is it delivered?
2. Revenue per month and trend over the last 6 months. Gross margin %.
3. New customers per month. Where do they come from (warm outreach, content, cold outreach, paid ads, referrals, affiliates)?
4. Leads per month → booked → showed → closed (or site visits → purchases).
5. CAC, average lifetime value / months retained, monthly churn.
6. Team: who sells, who delivers, what the owner still does daily.
7. The goal (number + date) and what they think is stuck.

If they point to a notes folder or file, read it instead of asking.

## 2. Analyse
- Compute: LTGP (lifetime gross profit) : CAC ratio, payback period, revenue ceiling = new customers per month ÷ churn rate, close rate.
- Place them on his scaling stages and the constraint for that stage (`h search "scaling roadmap stage <n> constraint"`, and `h frameworks` for the stage cards).
- Pick ONE constraint among: offer, price, leads (volume), conversion (sales), retention/churn, delivery capacity, team/owner time.
- Pull 8–14 searches across books, coaching calls and `--kind case` on that constraint and on businesses like theirs; `get` the best hits.

## 3. Report (write to `~/Documents/Hormozi Reports/<business>-<YYYY-MM-DD>.md`, and summarise in chat)
Sections: The verdict (one paragraph, blunt) · Your numbers (table) · The constraint and why · The plan (next 7 days, next 30, next 90 — concrete actions, owner and metric for each) · What NOT to do yet · The math (before/after) · Sources (book pages + timestamped videos).
Voice: his. Language: the user's. Always run `h search` in English, whatever language the user writes in.
