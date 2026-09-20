# PROTOTYPE, THROWAWAY: CHI hypergraph authority store

Answers one question: **does the accepted CCGF doctrine hold up when implemented as a SQLite authority store, or do hard cases expose gaps?** Results are in `FINDINGS.md`.

```
python3 scenarios.py            # all scenarios
python3 scenarios.py fund       # one: happy fund beta tier4 lifecycle dsn path ledger combos
```

- `hypergraph.py`: the store (schema, the four boundaries, the admission state machine, the ambiguity allowance, lineage, receipts). Stdlib only; SQLite in memory by default, or a file when given a path (the glossary store uses one).
- `scenarios.py`: replays the doctrine's own hard cases and prints the state after each step.
- `FINDINGS.md`: what held and 19 gaps found.
- `glossary/`: the CHI glossaries (permission gate and CCGF) loaded into this store, with a query tool. See `glossary/README.md`.

**Assumption stated up front:** the `prototype` skill's default for a state-model question is a single HTML file with in-memory state and no tests. This one is Python and SQLite because that was the accepted plan and because SQLite is part of what is being tested (foreign keys, append-only receipts, terminal states enforced by the database). It is still throwaway: no framework, no abstractions, and the store is separate from the runner. The scenarios run in memory; only the glossary store is persisted, to a file marked rebuildable. The scenario runner is the check, not a test suite.

Not production code. It touches nothing in `chi-platform/`. The scenarios use invented data; the only real content is the CHI glossary in `glossary/`, read from the source Markdown files and rebuildable from them. Delete the folder when done, or lift `hypergraph.py` into the real module once the gaps in `FINDINGS.md` are decided.
