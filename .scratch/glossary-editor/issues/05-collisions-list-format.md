# Collisions list: the structured format in CONTEXT-MAP.md

Type: prototype
Status: open
Blocked by:

## Question

Collisions ("must not be confused with") are hard-coded in `glossary.py` and matched against prose lines in `CONTEXT-MAP.md`. The charting decisions say they become a small structured list in `CONTEXT-MAP.md` that the loader parses and the editor edits. What should that section look like, and how does the loader read it? Make a rough, reactable version: a candidate `CONTEXT-MAP.md` section (in a scratch copy, not the real file) covering a term-to-term collision and a term-to-outside-usage collision, and what the loader would parse from it. Decide:

- How a pair is written so a human reads it and the loader parses it without ambiguity.
- How an outside usage is named, and where its "where it is used" comes from.
- What happens to the map's existing prose lines and to the hard-coded lists (a one-time migration).
- What the loader does when a pair names a term that is not defined (it must still fail loudly).
