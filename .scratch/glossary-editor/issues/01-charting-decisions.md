# Charting decisions (Q1–Q18)

Type: grilling
Status: resolved
Blocked by:

## Question

What are the destination, scope and standing decisions the whole effort stands on?

## Answer

Settled across three grilling rounds. Every recommendation was accepted.

**Round 1: destination and scope**
- Destination is a locked decision set plus a build spec for the next version of the editor. The map plans; it does not build.
- One user, on this machine. No accounts; the identity is the name typed for verification. Anything else is out of scope.
- Keep editor v1 as the prototype to build from. The spec lists deltas from it.
- The destination includes store semantics: how the store treats changing, removing and renaming admitted knowledge (a doctrine and loader question). Doctrine edits stay drafts until the user says go.
- The editor and its docs say **term**, not "entry": "entry" already means an audit-log entry in the permission gate glossary, and CCGF avoids "log entry".
- The map lives in `.scratch/glossary-editor/` as local markdown, like the permission-gate map. Nothing is published to GitHub.
- Out of scope: editing anything but the two glossaries; hosting or multi-user; automating verification; the old `prototype-hypergraph/` store.

**Round 2: the shape of v2** (the doctrine already defines revision: admitted, under review, revised, closed, with a new item that records its predecessor and an earlier one never resumed; the store has the primitives, but the loader uses none of them)
- A changed term follows the doctrine's revision path: the old claim is revoked and a **new** claim is proposed with the old one as its predecessor, then a human verifies it. Drift-plus-rebuild is retired as the answer.
- A removed term or avoided word is *reported* by the loader; a **human** revokes it, with a note. The action is called **revoke**, never "delete".
- Collisions become a small structured list in `CONTEXT-MAP.md` that the loader parses and the editor edits.
- Verify stays a command the page builds (never run by the page), but it shows the exact source text being attested.
- History and undo belong to git. The editor never commits or pushes.

**Round 3: the window and the deliverables**
- Between an edit and its re-verification the old claim stops being asserted at once (challenged), so `define` and the lint hook go quiet on that term. Principle: the machine may only make the store less assertive; only a human makes it more assertive (verify) or final (revoke).
- Renaming a term is not an act in v2: it is a revoke plus a new term.
- **Drift** (a loaded claim whose source text has since changed) and **Outside usage** (a phrase quoted from outside both glossaries) are drafted for `docs/ccgf/CONTEXT.md`, applied only with the user's go-ahead.
- The spec lives at `docs/glossary-editor/SPEC.md`, next to `docs/permission-gate/`.
- The editor stays in `chi` (the Markdown lives there). Its dependency on `chi-platform` (the `CHI_GATEWAY_DIR` path and the loader's CLI) is documented in the spec and revisited if the gateway's API shifts.
- Performance is out of scope apart from two notes in the spec.

**Facts measured while charting** (scratch stores of 267, 1,467 and 4,267 claims; the real store untouched)
- Load, verify and the integrity check are all linear (load about 2.5 ms per claim; integrity 0.96 s at 4,267 claims). `define` and `lint` each re-run the whole integrity check.
- Foreign keys are enforced (`ledger._connect()` sets `foreign_keys = ON`). Eight foreign-key columns have no index, which is harmless because they are scanned only when a parent key changes and the append-only triggers forbid that.
- `hyperedge_members` is indexed in both directions, so reverse lookups need nothing new.
- **A design point for v2:** the candidate-evidence insert uses a separate connection from the hypergraph transaction, so a revise (revoke the old claim, propose the new one with lineage) must be atomic or safely resumable. See [Revise mechanics](03-revise-mechanics.md).
