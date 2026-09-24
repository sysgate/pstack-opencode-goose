# Revise mechanics: what happens when a term changes

Type: grilling
Status: resolved
Blocked by:

## Question

The charting decisions say a changed term follows the doctrine's revision path and the old claim stops being asserted at once. Given what the store actually allows, decide the exact mechanics for the spec:

- What counts as a **change**, element by element: the definition text, an avoided word added or removed, an avoid note changed, the group changed.
- The sequence of states and receipts for the old claim (challenged on load, then revised or revoked when the new one is verified) and for the new claim (proposed with the old one as predecessor), and who acts at each step.
- Whether a revise is **one atomic unit** or a **safely resumable** sequence, given that the candidate-evidence insert uses a separate connection.
- What the loader reports and what `status` shows during the window.
- What happens when the same term is edited again before the first revision is verified.

Facts from [The store's lifecycle facts](02-store-lifecycle-facts.md) that these decisions must answer:

- Reopen works only from a terminal claim, so the sequence has to run challenge, begin review, revise, close, reopen. Which of those steps are taken at load and which at verification?
- Which `sys:` name does the editor or loader act as: `sys:adjudicator` (defined as acting "for cascades no person decided") or a new one? Either passes the store's check.
- The loader cannot see a successor claim (ids are computed without predecessors) and never inserts a candidate for changed text. How does it find the successor, and how do `status` and `verify` treat a closed predecessor?
- Should the old claim's evidence be revoked when it is revised? The library allows it and it voids the old binding; no doctrine text says it should happen.
- The candidate-evidence insert cannot share the hypergraph transaction from its own connection. Is a same-connection insert acceptable, or is the sequence made resumable instead?
- A reopened claim is stored with its copied confidence but no uncertainty receipt. Intended, or a gap the spec should close?
- Two loader defects to fold in: `status` can report a negative "not loaded" count, and `verify` can list a claim as both verified and refused.
- The collisions table ([Collisions list](05-collisions-list-format.md)) is the first thing to go through this path: all six existing collision claims change evidence text at once. The mechanics must handle a batch of revisions cleanly, and the human verifies them with real notes.

## Answer

Settled with the user across two grilling rounds; every recommendation was accepted. The store facts behind it are in [The store's lifecycle facts](02-store-lifecycle-facts.md).

**What counts as a change** is decided by a claim's members.
- Same members, different source text is a **revise**: the definition text, and the `_Avoid_:` line for aliases that stay with the same note.
- New members make a **new claim**: a new avoided word, a changed avoid note (the note is a member), a changed group.
- Members that vanish are a **removal**, decided in [Removal and revoke](04-removal-and-revoke.md).
- An avoid claim's evidence stays the **whole `_Avoid_:` line**, so adding a word to a term with three avoided words revises those three claims and adds one. Per-alias evidence was rejected: it would change the evidence of all 143 avoid claims at migration.
- A term's label cannot be revised in the store (only revoked or reopened), so a rename is a revoke plus a new term.

**Load (the machine step), per source statement whose current text differs from its admitted text**
1. Insert a candidate for the current text on its own connection, if absent.
2. In one hypergraph transaction, if the current claim is `ADMITTED`, **challenge** it as `sys:adjudicator` with the reason "source text changed" (REVISION_OPEN). From then on the claim is withheld: `define` and the lint hook go quiet on it.
- The **current claim** is found by following the chain of computed ids (no predecessors, then with the first as predecessor, and so on), taking the last that exists. No schema change.
- **Resumable, not atomic.** A crash between the two steps leaves an orphan candidate and a still-admitted claim; a rerun finishes, because it challenges only an admitted claim whose current text differs. Every intermediate state is legal and withheld. The candidate insert stays on its own connection; the gateway is not changed.
- **Editing again before verification:** stale candidates are left as they are. Verify only ever binds the candidate for the current text, so they are never asserted and never bound.

**Verify (the human step, `--by human:NAME --note "..."`), one transaction per claim, three cases**
- **New claim** (loaded, unverified): as today.
- **Revision** (the current claim is challenged and a candidate exists for the current text): as the human, begin review, resolve as revised (with the note), close the old claim; then reopen a **successor** that names it as its predecessor; set its uncertainty explicitly (so it carries an uncertainty receipt like every other claim); admit the new evidence (human, with the note); bind it; admit the successor.
- **Revert** (the current text matches evidence that is still admitted and bound to the challenged claim): as the human, begin review and **reaffirm**. A removed entry that is put back while its claim is still challenged is reaffirmed the same way. Reaffirming makes the store more assertive, so it is a human step.
- **Actors:** the human named by `--by` for begin review, revise, close, reaffirm and the evidence admit, so the receipts say who made it final; `sys:adjudicator` for the mechanical steps (reopen, uncertainty, bind, admit the successor).
- **Per claim, not per term.** A partial result is legal because unverified revisions stay withheld. The report says what succeeded and what did not, and lists a claim as verified only after its transaction has committed.
- The **old evidence is left admitted**: it is an accurate record of what the source said then; revoking would say it was wrong. (This is also why a revert can be reaffirmed.)

**What `status` and the editor show.** Every claim in the sources lands in exactly one bucket, so the counts always add up:
- **not loaded** (new)
- **drift**: an edit was saved but not yet loaded (the word is narrowed to this moment)
- **loaded, unverified** (a new claim)
- **revision awaiting verification** (the old claim is challenged, the new text pending)
- **verified**
- **awaiting reaffirm** (a reverted edit, or a removed entry put back while its claim is still challenged: the text matches evidence that is still admitted; see [Editor v2 screens](07-editor-v2-screens.md))
- **restored, awaiting verification** (a revoked or denied claim whose statement is back in the sources; see [Removal and revoke](04-removal-and-revoke.md))
- **needs attention** (a state the loader never produces)

Claims in the store that are no longer in the sources are reported separately, by [Removal and revoke](04-removal-and-revoke.md).

**Words.** The new claim is the **successor**; **Successor** and **Predecessor** are defined beside **Lineage** in the drafted glossary text, applied only with the user's go-ahead like **Drift** and **Outside usage**. Docs say "revise" for the store's act and "edit" for the person's action in the editor (the glossary lists "editing" as an avoided word for revision governance).

**Two loader defects folded into the spec:** `status` printing a negative "not loaded" count (fixed by the partition above), and `verify` listing a claim as both verified and refused when its transaction rolls back (fixed by reporting after commit).

**What changes in the loader** (deltas for the spec): follow the id chain to find the current claim; the load-time candidate-plus-challenge step; the three verify cases; the status partition; the report fix. **First exercise:** the six collision claims move to the collisions table ([Collisions list](05-collisions-list-format.md)) through this path.
