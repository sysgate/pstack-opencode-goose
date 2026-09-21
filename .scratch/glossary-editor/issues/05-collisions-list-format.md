# Collisions list: the structured format in CONTEXT-MAP.md

Type: prototype
Status: resolved
Blocked by:

## Question

Collisions ("must not be confused with") are hard-coded in `glossary.py` and matched against prose lines in `CONTEXT-MAP.md`. The charting decisions say they become a small structured list in `CONTEXT-MAP.md` that the loader parses and the editor edits. What should that section look like, and how does the loader read it? Make a rough, reactable version: a candidate `CONTEXT-MAP.md` section (in a scratch copy, not the real file) covering a term-to-term collision and a term-to-outside-usage collision, and what the loader would parse from it. Decide:

- How a pair is written so a human reads it and the loader parses it without ambiguity.
- How an outside usage is named, and where its "where it is used" comes from.
- What happens to the map's existing prose lines and to the hard-coded lists (a one-time migration).
- What the loader does when a pair names a term that is not defined (it must still fail loudly).

## Answer

Settled with the user; every recommendation was accepted. The rough version, with rough parsers and four checks over the six real collisions, is the throwaway [prototype](../prototype/collisions-format.PROTOTYPE.py) (uncommitted, like everything in this effort).

**Format: a table in `CONTEXT-MAP.md`, one row per pair** (variant B of four: a line per pair, a table, grouped by word, or hidden comments over the prose).

```
## Collisions

| Term | In | Must not be confused with | In | Why |
|---|---|---|---|---|
| Scope | Permission gate | Scope | CCGF hypergraph | a folder tree in the gate, an operational namespace in CCGF |
| Fast path | Permission gate | fast-path / diagnostic | outside: docs/ARCHITECTURE.md | a router route CCGF does not define |
```

- The first side is always a defined term. The second side is a defined term, or an **outside usage** marked by `outside: <where>` in its "In" cell, so the "where it is used" is data, not punctuation.
- The evidence for each collision claim is its own row, byte for byte. Editing one row changes the evidence of one claim; grouping by word would change several, and expanding a group into every pair wrongly implies that every pair collides (the two System layers do not collide with each other).
- The loader parses the table and **fails loudly**, naming the section, when the section is missing or empty, a row does not have five cells, a row names a glossary or a term that is not defined, or a pair is written twice in either order.
- The hard-coded lists in `glossary.py` (`COLLISIONS`, `OUTSIDE_USAGES`) and the sentence-matching they need are removed.

**The prose in `CONTEXT-MAP.md`.** The two prose lines that state collisions (the "Same word, different meaning" and "More same-word collisions" bullets) are trimmed so the table is the only statement. The "independent" relationship line stays, and so does the note that "Admission gate" belongs to CCGF and is avoided in the gate context (that is an avoid entry, not a collision). This is a draft for the spec; the file is not edited until the user says go.

**Migration.** Every structured format changes all six existing collision claims' evidence (today two prose lines back them). The six are **revised once** through v2's revise path ([Revise mechanics](03-revise-mechanics.md)), each re-verified by a human with a real note. This is the first exercise of that path, and it also replaces the three outside-usage claims whose receipts carry the placeholder note `...`.

**Left to the spec:** the rule for `|` and line breaks inside a cell (refused), and whether the "Why" cell is required (proposed: required and non-empty).
