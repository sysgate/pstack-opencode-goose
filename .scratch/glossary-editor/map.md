# Map: The CHI glossary editor, v2

## Destination

A locked set of decisions and a build spec (`docs/glossary-editor/SPEC.md`) from which version 2 of the glossary editor can be built, with nothing left to decide before someone builds it. The destination is the spec, not the build. It has to say, in particular, how a changed or removed term moves through the store's revision lifecycle without a full rebuild.

## Notes

- **Domain**: a local web app (`hypergraph-db/glossary-editor/`; version 1 is built and was still uncommitted when this map was charted) that edits the two glossary Markdown files (`CONTEXT.md`, `docs/ccgf/CONTEXT.md`) and drives the glossary loader (`chi-platform/infra/chi_agent_gateway/app/hypergraph/glossary.py`) against the prototype database. Vocabulary is in `CONTEXT-MAP.md`, `CONTEXT.md` and `docs/ccgf/CONTEXT.md`. The revision lifecycle is in the doctrine (`AGENTS.md`, `docs/ARCHITECTURE.md`). Core rule: generation proposes, governance admits.
- **Skills to consult**: `mattpocock-skills:domain-modeling` (keep the glossaries current), `mattpocock-skills:research`, `mattpocock-skills:prototype`.
- **Prototype to build from**: editor v1 (`hypergraph-db/glossary-editor/server.py`, `page.html`, its 40 tests) and the loader's `build_plan(..., overrides=)`. The spec must list its deltas from v1.
- **Standing preferences**: single user, local, no accounts. Markdown is the source of truth and the store is loaded from it. The editor and its docs say **term**, never "entry" ("entry" already means an audit-log entry in the gate glossary). A machine may only make the store *less* assertive (challenge, withhold); only a human makes it more assertive (verify) or final (revoke). Nothing is deleted: the action is **revoke**, with a receipt. The editor never commits or pushes. No doctrine or glossary edit is applied without the user's go-ahead. Anything run against a store uses a scratch copy, never the real prototype database.
- **Tracker**: local markdown. Tickets are `issues/NN-slug.md` with `Type:`, `Status:`, `Blocked by:` lines. Research findings go in `research/`.

## Decisions so far

<!-- one line per closed ticket -->

- [Charting decisions (Q1–Q18)](issues/01-charting-decisions.md): destination is a spec, not a build; single user and local; keep v1 as the base; a changed term follows the doctrine's lineage path and the old claim is withheld at once; removals are reported and a human revokes; collisions become a structured list; verify stays a command that shows the exact source text; git owns history; rename, performance work and hosting are out.

## Not yet specified

<!-- in scope, but not sharp enough to ticket yet -->

- **Rename as one act.** Unsupported in v2 (a rename is a revoke plus a new term). Returns once revise works, if the extra claims a rename touches (avoid aliases, group, collisions) turn out to be manageable.
- **The three collision claims verified with the note `...`.** Their receipts do not say what was reviewed and cannot be edited. Revoking and re-verifying them is the first real use of revoke, so it waits on how revoke works.
- **What readers say about a withheld term.** `define` and the lint hook go quiet while a term is being revised. Whether they should say so, and how, depends on the revise mechanics.
- **Refreshing the hypergraph web view after a save.** The view is a snapshot; whether the editor regenerates it or links to it is not yet a sharp question.
- **How v2 is tested.** The scratch-store harness, sabotage probes and browser checks worked for v1; what v2's new operations need on top is not yet known.

## Out of scope

<!-- ruled beyond the destination; never graduates -->

- Editing anything other than the two glossaries (evidence, doctrine, other hypergraph data).
- Hosting, remote access, multi-user or accounts. The identity is still the name the person types.
- Automating verification. It stays a human act.
- The older `prototype-hypergraph/` store.
- Performance work beyond two notes for the spec: reuse one connection in the evidence insert if rebuilds ever feel slow, and watch the per-call integrity cost in the lint hook past roughly 10,000 claims. (Measured: load is linear at about 2.5 ms per claim.)
- Building v2. The destination is the spec.
- Editor-owned history, undo or commits. The Markdown is in git.
