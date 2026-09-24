# Constraint Split Testing (one test per week per platform)
slug: constraint-split-testing · category: scaling · aliases: better, drop-off points, testing schedule, test log, Monday split test

## What it is
The "better" in [[more-better-new]]. You run more until it breaks (CAC climbs past what you can sustain), then improve the funnel one step at a time. Every step a lead takes before buying is a possible drop-off; the step losing the most people is the **constraint**, where tiny gains produce the largest lift. Hormozi says thousands of small tests are what separate winners from beginners.

## How to apply it
1. Map every step from first touch to sale with its conversion rate.
2. Find the biggest drop-off. Test there first.
3. **One test per week per platform.** Every Monday launch one split test; the next Monday:
   - pick the winner,
   - record the result in a permanent log of all tests (so you never restart from zero),
   - design the next challenger to beat the current best.
4. If four tries (about a month) can't beat the control, move to the next constraint.
5. When improvements yield less than new effort elsewhere would, move on to "new."

## When to reach for it
After scaling volume has pushed costs up, or when a funnel has one obviously leaky step.

## Mistakes he warns about
- Testing several things at once on one platform: you never learn what worked, and steps influence each other (a change that lifts opt-ins might lower applications).
- Wasting your one big weekly test on trivia, such as swapping one shade of red for another.
- Running tests too briefly (not enough data) or too long (lost time on the next constraint). One week fits his team and spend; smaller operations may need longer.

## The math
Funnel of 30% opt-in, 5% apply, 50% schedule. Adding 5 points to each step alone:
- opt-in 30 to 35% = about 1.16x leads
- apply 5 to 10% = 2x leads (the constraint)
- schedule 50 to 55% = 1.1x leads
Same effort, wildly different payoff; fix the constraint.

## Sources
- $100M Leads, pp. 237–239, 244

## Related
[[more-better-new]], [[rule-of-100]], [[ltgp-to-cac]]
