# The CHI glossary, stored in the prototype hypergraph store

**PROTOTYPE data, rebuildable.** The two glossaries (`CONTEXT.md`, the permission gate; `docs/ccgf/CONTEXT.md`, CCGF) and the collisions in `CONTEXT-MAP.md` are loaded into `chi-glossary.PROTOTYPE-rebuildable.sqlite3`. **The Markdown files stay authoritative;** delete the `.sqlite3` any time and rebuild it.

```
python3 glossary_load.py --rebuild          # (re)build the store from the source files
python3 glossary_cli.py term "Scope"        # every context's definition, group, avoided aliases, collisions
python3 glossary_cli.py avoid "node"        # what to say instead, with the qualifying note
python3 glossary_cli.py collisions          # same word, different meaning, both definitions side by side
python3 glossary_cli.py groups
python3 glossary_cli.py stats
python3 glossary_cli.py verify              # round trip against the source files + store integrity
python3 glossary_viz.py                     # offline, clickable map of the CURRENT store (../../hypergraph-db/); pass --db <this file> for this old one
```

## What is in it

| Kind | Count | How it is stored |
|---|---|---|
| Terms | 73 (28 gate, 45 CCGF) | a semantic object scoped to its context, so "Scope" in the gate and in CCGF are two objects |
| Avoided aliases | 133 objects, 135 claims | an object per alias per context; 7 claims carry a qualifying note as a `CONDITION` |
| Contexts, groups, predicates | 2, 3, 4 | semantic objects |
| Claims | 256 | `CLAIM(SUBJECT, PREDICATE, OBJECT)`: 73 "is defined in", 45 "belongs to group", 135 "is avoided in favour of", 3 "must not be confused with" |
| Evidence | 256 | the source text of each claim, `TIER_3_EXTRACTED`, bound `SUPPORTS` |

Every object went through DSN (narrowed on a recorded basis, with the alternative meanings considered) and semantic admission; every claim went through all four boundaries. Each claim says "the source states this", not "the statement is correct", so its confidence bound is 1.0.

## How far to trust it

`verify` reopens the file fresh and checks that all 73 definitions, 135 avoid lists, 7 notes, every group membership and the 3 collision lines equal the source files (a stale store fails), that everything is admitted, that the receipt chain verifies, and that the store's own evidence and state agree with its receipts. I attacked a copy four ways (a forged definition with a correct hash, a deleted claim, a deleted object, a planted admitted row); the store alone catches all four, after a fix described in `../FINDINGS.md` F17.

Limits: this is the throwaway prototype (six known gaps, see `../FINDINGS.md`), the evidence is unverified extraction (F19), and nothing reads from it except this tool.
