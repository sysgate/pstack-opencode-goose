# Map: The CHI glossary editor, v2

## Destination

A locked set of decisions and a build spec (`docs/glossary-editor/SPEC.md`) from which version 2 of the glossary editor can be built, with nothing left to decide before someone builds it. The destination is the spec, not the build. It has to say, in particular, how a changed or removed term moves through the store's revision lifecycle without a full rebuild.

## Notes

- **Domain**: a local web app (`hypergraph-db/glossary-editor/`; version 1 is built and was still uncommitted when this map was charted) that edits the two glossary Markdown files (`CONTEXT.md`, `docs/ccgf/CONTEXT.md`) and drives the glossary loader (`chi-platform/infra/chi_agent_gateway/app/hypergraph/glossary.py`) against the prototype database. Vocabulary is in `CONTEXT-MAP.md`, `CONTEXT.md` and `docs/ccgf/CONTEXT.md`. The revision lifecycle is in the doctrine (`AGENTS.md`, `docs/ARCHITECTURE.md`). Core rule: generation proposes, governance admits.
- **Skills to consult**: `mattpocock-skills:domain-modeling` (keep the glossaries current), `mattpocock-skills:research`, `mattpocock-skills:prototype`.
- **Prototype to build from**: editor v1 (`hypergraph-db/glossary-editor/server.py`, `page.html`, its 40 tests) and the loader's `build_plan(..., overrides=)`. The spec must list its deltas from v1.
- **Standing preferences**: single user, local, no accounts. Markdown is the source of truth and the store is loaded from it. The editor and its docs say **term**, never "entry" ("entry" already means an audit-log entry in the gate glossary). A machine may only make the store *less* assertive (challenge, withhold); only a human makes it more assertive (verify) or final (revoke). The store does not enforce this (a `sys:` actor may revoke), so it is policy the loader and editor must enforce. Nothing is deleted: the action is **revoke**, with a receipt. The editor never commits or pushes. No doctrine or glossary edit is applied without the user's go-ahead. Anything run against a store uses a scratch copy, never the real prototype database.
- **Tracker**: local markdown. Tickets are `issues/NN-slug.md` with `Type:`, `Status:`, `Blocked by:` lines. Research findings go in `research/`.

## Decisions so far

<!-- one line per closed ticket -->

- [Charting decisions (Q1–Q18)](issues/01-charting-decisions.md): destination is a spec, not a build; single user and local; keep v1 as the base; a changed term follows the doctrine's lineage path and the old claim is withheld at once; removals are reported and a human revokes; collisions become a structured list; verify stays a command that shows the exact source text; git owns history; rename, performance work and hosting are out.
- [The store's lifecycle facts](issues/02-store-lifecycle-facts.md): a `sys:` actor may challenge an admitted claim; revoke is not human-only in the store (editor policy); reopen makes a new claim but only from a terminal state, so a revise runs challenge, review, revise, close, reopen; the loader cannot see a successor or bind changed text; findings in `research/02-store-lifecycle-facts.md`.
- [Collisions list: the structured format in CONTEXT-MAP.md](issues/05-collisions-list-format.md): a table in `CONTEXT-MAP.md`, one row per pair, an `outside:` marker for phrases used elsewhere; the row is each claim's evidence; the loader fails loudly on a missing or bad section; the two prose collision lines are trimmed (a draft until the user says go); the six existing collision claims are revised once.
- [Revise mechanics: what happens when a term changes](issues/03-revise-mechanics.md): a change is decided by a claim's members (same members and new text is a revise); load inserts a candidate and challenges the old claim, verify (a human, per claim) revises, closes and reopens a successor, or reaffirms a reverted edit; the old evidence stays admitted; `status` becomes a partition; two loader defects folded in.
- [Removal and revoke: how a term leaves the glossary](issues/04-removal-and-revoke.md): a claim not in the sources is removed (never guessed as a rename); load withholds it at once, a human revokes it with one guarded command (or denies it if never verified); claims only, terms stay; a put-back entry is reaffirmed or reopened as a successor; the editor gets a Remove term action and a removed-claims panel.
- [What readers say about a withheld term](issues/09-what-readers-say-about-a-withheld-term.md): `define` reuses the doctrine's projection labels verbatim with a reason from a closed list, one line per current claim (earlier versions only counted), integrity fault first, never instructing; the lint hook stays silent; `status` and the editor name the next step and show the same strings.
- [The verify panel: showing the exact source text](issues/06-verify-panel-source-text.md): the panel shows each pending claim by case (new, revision with old and new text, reaffirm, restored); `verify` requires an explicit selection plus a `--confirm` digest over the exact claims and text, so it refuses if the source changed after you looked; revoke uses the same guard; name and note rules live in the loader; one note per run; the page refreshes on focus.
- [Editor v2 screens](issues/07-editor-v2-screens.md): term-centred layout (the user chose variant C of a three-variant prototype): each term's page has the v1 form above a table of its claims (state, projection label and reason, next step), an inline Remove term consequences box that refuses while a collisions row names the term, a collisions table screen, and an inline "The database" panel with Load, Verify and Revoke builders (no drawer); reaffirms get their own pill, awaiting reaffirm.

## Not yet specified

<!-- in scope, but not sharp enough to ticket yet -->

- **Rename as one act.** Unsupported in v2 (a rename is a revoke plus a new term). Returns once revise works, if the extra claims a rename touches (avoid aliases, group, collisions) turn out to be manageable.
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
