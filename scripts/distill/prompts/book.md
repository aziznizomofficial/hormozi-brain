You are building a public, copyright-safe study index of Alex Hormozi's book "{book}". You read a run of pages (extracted PDF text, "=== p. N ===" marks each page) and write paraphrased claims that point back to exact pages and section headings. Readers will use it to know what the book teaches and where, then go read the original. It is an index of ideas, NOT a summary or abridgment of the book: skip narrative, anecdotes' wording and transitions; keep the ideas.

PAGES {start}–{end}
{text}

KNOWN FRAMEWORK SLUGS (tag claims with these when they fit; for a named model of his not in the list use "new:<Name>")
{frameworks}

WRITE, as one JSON object:

"sections": each section heading that starts on these pages. {{"page": N, "heading": the heading text as printed (headings are titles and may be copied), "topic": max 15 words in your own words}}. [] if none.

"claims": the ideas worth finding again, in this priority: definitions of his named models, steps of named processes, numbers and rules of thumb, warnings, then principles. DENSITY LIMIT: on average at most 1 claim per page across this run (never more than 2 on any page); many pages will have none. This is an index for finding ideas, not a retelling: skip anecdotes, examples, persuasion, front matter, dedications and ads for his other products.
  {{"text": max 40 words, "page": the page where it is stated, "section": the nearest heading above it (from these pages or, if none, the best guess of the running chapter, else ""), "type": one of principle|tactic|benchmark|definition|warning|story|belief|step, "frameworks": [slugs]}}
  - Self-contained and specific: keep conditions and every number.
  - Faithful: never add, never generalise beyond what the page says; no reasons or consequences the page does not give.
  - "step" = one step of a named multi-step process; start the text with the process name and step number, e.g. "Grand Slam Offer, step 3: …".

WORDING RULES (hard):
- Your own plain English words. Never reuse more than 6 consecutive words from the pages, except names, titles, numbers and his coined framework names.
- No quotes, no quotation marks, no reproducing his examples' scripts, templates or lists verbatim; describe what they do instead.
- Refer to him as "he" or "Hormozi"; never first person.

Reply with ONLY the JSON object: no prose, no code fence, no tools, no files.
