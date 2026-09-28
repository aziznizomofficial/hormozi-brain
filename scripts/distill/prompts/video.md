You are building a public, copyright-safe study map of Alex Hormozi's public videos. You read one transcript (YouTube auto-captions: no punctuation, no speaker labels, some mis-heard words) and write a paraphrased map of it that points back to exact timestamps. Readers will use your map to find what he said and where, then go watch the original.

SOURCE
Title: {title}
Channel / kind: {source} ({kind_note})
Published: {date}
Chunk labels you may cite: each chunk starts with [mm:ss] or [h:mm:ss]; cite labels exactly as written, without brackets.

TRANSCRIPT
{text}

KNOWN FRAMEWORK SLUGS (tag claims with these when they fit; for a named model of his not in the list use "new:<Name>")
{frameworks}

WRITE, as one JSON object:

"summary": 2–3 sentences, max 60 words: what this video/part covers and who is speaking (solo, interview host, coaching caller…).

"segments": one entry for EVERY chunk label, in order. {{"t": label, "topic": max 18 words saying what is discussed there, "tags": 2–5 short lowercase topic tags}}. Filler, intros and ad reads: topic "intro", "promo" or "off-topic".

"claims": the ideas worth finding again. One claim = one idea HE states (not the host, not a caller). Roughly one per 1–2 minutes of substantive advice, max 60, none for small talk.
  {{"text": max 40 words, "t": [1–2 labels where he says it], "type": one of principle|tactic|benchmark|definition|warning|story|belief, "frameworks": [slugs]}}
  - Self-contained: someone who never saw the video understands it. Keep the condition (who it applies to) and every number he gives.
  - Faithful: never add advice he did not give, never merge ideas from different moments, never upgrade "I think" into a rule. If a number was garbled by the captions, leave the number out.
  - Advice given to one specific business goes in "cases", not "claims", unless he states it as a general rule.
  - Never add reasons, mechanisms or consequences he did not state. If he frames something as a guess or opinion, keep that ("he suspects", "he thinks").
  - "t" = the chunk where he actually states the idea, not where the topic is first mentioned.
  - "story" = a fact about his own life or companies. "benchmark" = a number, ratio or rule of thumb.

"cases": only REAL businesses discussed with concrete facts: a caller or guest's business, one of his own or portfolio companies, or a named company he analyses. Skip hypothetical and illustrative examples ("say you run a gym…"). [] if none. {{"business": type, size, location if said — NO personal names, "numbers": the figures stated (revenue, price, margin, CAC, churn…) or "", "question": what they asked or were stuck on, "diagnosis": the constraint he named, "advice": 1–5 short steps he prescribed, "t": [first label, last label]}}

WORDING RULES (hard):
- Write in your own plain English words. Never reuse more than 6 consecutive words from the transcript, except names, book titles, numbers and his coined framework names (e.g. Grand Slam Offer, Core Four, Value Equation).
- No quotes, no quotation marks.
- Refer to him as "he" or "Hormozi"; never write as him in first person.
- English only.

Reply with ONLY the JSON object: no prose, no code fence, no tools, no files.
