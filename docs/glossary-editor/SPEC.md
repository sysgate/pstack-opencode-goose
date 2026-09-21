# CHI glossary editor v2: specification

Status: **accepted at review** (2026-09-20): the user accepted the recommendations on the review questions in section 11. This is the hand-off for building version 2 of the glossary editor and the loader changes it depends on. Nothing here is built, and no doctrine or glossary file has been changed. It was assembled from the wayfinder map in `.scratch/glossary-editor/` (see the decision index in section 13); every decision below was made with the user; section 11 records the last review answers.

## 1. What it is

Editor v1 (`hypergraph-db/glossary-editor/`) is a local web page that adds and edits terms in the two glossary Markdown files, previews the effect on the hypergraph, saves, and loads new claims. Its limit is that a *changed* term shows as drift and can only be fixed by rebuilding the prototype database, a *removed* term is never noticed, and collisions are hard-coded.

Version 2 lets a person **revise, remove and restore terms and record collisions** without a rebuild, by mapping each Markdown change onto the revision lifecycle the doctrine and the store already have (a revised claim is a new claim that names the old one as its predecessor; an earlier one is never resumed). Most of the work is in the loader (`chi-platform/infra/chi_agent_gateway/app/hypergraph/glossary.py`); the editor becomes a view over it.

## 2. Goals, non-goals, standing rules

**Goals.** A change to a glossary source moves through the store safely and visibly: withheld at once, finalised by a human, with a receipt trail. The person can see, for every claim, what the store says and what to do next.

**Non-goals (out of scope for v2).**
- Editing anything other than the two glossaries (evidence, doctrine, other hypergraph data).
- Hosting, remote access, multi-user or accounts. Identity is still the name the person types.
- Automating verification. It stays a human act.
- The older `prototype-hypergraph/` store.
- Regenerating or extending the hypergraph web view to show these states: it stays a snapshot, and the editor does not regenerate it.
- Renaming a term as one act (a rename is a revoke plus a new term; it may return as its own effort once revise works).
- Editor-owned history, undo or commits. The Markdown is in git; the editor never commits or pushes.
- Performance work beyond the two notes in section 10.

**Standing rules** (from the map's Notes):
- Markdown is the source of truth; the store is loaded from it.
- Words: **term** (never "entry": in the gate glossary an entry is an audit-log entry), **revise** for the store's act and **edit** for the person's, **revoke** for a human finalising an admitted claim, **deny** for a claim never verified, **remove** for deleting from the Markdown.
- **A machine may only make the store less assertive** (challenge, withhold), immediately and reversibly. **Only a human** makes it more assertive again (verify, reaffirm) or final (revoke, deny). The store does not enforce this (a `sys:` actor can revoke, with an empty note), so it is policy the loader and editor must enforce.
- Nothing is deleted from the store. No doctrine or glossary edit is applied without the user's go-ahead. Anything run against a store while building or testing uses a scratch copy, never the real prototype database.

## 3. The model in one page

A **claim** is a hyperedge (subject, predicate, object, optional condition) backed by the source text it came from (its *evidence*). Its identity is its **members**; its evidence text is what a person verifies.

| The Markdown change | Class | What happens |
|---|---|---|
| Same members, different source text: the definition, or the `_Avoid_:` line for aliases that stay with the same note | **revise** | the old claim is challenged; a successor is created when a human verifies |
| New members: a new avoided word, a changed avoid note (the note is a member), a changed group | **new claim** | loaded pending; a human verifies |
| Members vanish: a dropped alias, a removed term, a renamed term (the old term) | **removal** | the old claim is challenged; a human revokes it |

- An avoid claim's evidence is the **whole `_Avoid_:` line**. Adding a word to a term with three avoided words therefore revises those three claims and adds one. (Per-alias evidence was rejected: it would change the evidence of all 139 avoid claims at migration.)
- A term's **label** cannot be revised in the store (only revoked or reopened), so a rename is a revoke plus a new term.
- The loader **never guesses** that something was renamed or moved: a removed claim is one whose members are gone.
- The **current claim** of a source statement is found by following the chain of computed ids: the id with no predecessors, then the id with the first as predecessor, and so on, taking the last that exists. No schema change is needed.

**Who may do what** (the loader and editor enforce this; the store does not):

| Act | Actor | Effect on assertion |
|---|---|---|
| load: challenge a changed or removed admitted claim | `sys:adjudicator` | less assertive (withholds) |
| load: propose a pending claim, a candidate, or a successor | `adapter:glossary-md` / `sys:adjudicator` | none (pending is not asserted) |
| verify: review, revise, close, reaffirm, admit evidence | the human named by `--by` | more assertive or final |
| verify: reopen, set uncertainty, bind, admit the successor | `sys:adjudicator` | mechanical steps of the same transaction |
| verify: a restored claim whose text is unchanged | the human named by `--by` also acts on the bind and the admit | more assertive (there is no new evidence to admit, so this is where the human's attestation lands) |
| revoke or deny | the human named by `--by` | final |

## 4. The loader

All commands are `python -m app.hypergraph.glossary <command> --db PATH` and refuse the configured live ledger unless `--allow-live` is given. Notes and names are checked **in the loader**, not only in the page: the name has no spaces (`human:NAME`), and a note that is empty, a placeholder (`...`, `todo`, too short) is refused.

### 4.1 `load` (the machine step)

For each source statement whose current text differs from its admitted text:
1. Insert a candidate for the current text, on its own connection, if absent.
2. In one hypergraph transaction, if the current claim is `ADMITTED`, **challenge** it as `sys:adjudicator` with the reason "source text changed". From then on it is not asserted: `define` and the lint hook go quiet on it.

For a claim that is **removed**: if admitted, challenge it with the reason "no longer in the sources". A claim already challenged stays challenged. A pending claim is not asserted, so load leaves it.

For a claim whose statement is **back in the sources after being revoked or denied**: propose a **successor** (reopened from the revoked or denied claim, the only legal route because the id would otherwise be a duplicate) with a candidate.

- **Resumable, not atomic.** A crash between the candidate insert and the challenge leaves an orphan candidate and a still-admitted claim; a rerun finishes, because it challenges only an admitted claim whose current text differs. Every intermediate state is legal and withheld, never corrupt. The candidate insert stays on its own connection; the gateway is not changed.
- **Editing again before verification:** stale candidates are left alone. Verify only ever binds the candidate for the current text.
- The editor's Load button states, before it is pressed, how many claims it will withhold.

### 4.2 `verify` (the human step)

`glossary verify --by human:NAME --note "..." <selection> --confirm DIGEST`

- **Selection is required:** `--term T` (repeatable), `--anchor A`, or `--all-pending`. A selection-free `verify` is refused (a delta from today, where it verifies everything pending).
- **`--anchor A` selects only among claims that are pending or challenged.** An anchor is not unique (a changed avoid note leaves an old claim and a new one on the same anchor), and the digest covers claim ids, so an ambiguous selection changes it.
- **`--confirm DIGEST`** is a hash over the sorted lines `<claim id> | <case> | <candidate id>` of the selected claims. The candidate id already hashes the source location, anchor and text, so any change to the text, the selection or the case (someone else verified a claim; an entry was put back) changes the digest and the loader refuses: "the sources changed since the panel was rendered: refresh the page". This makes "the exact text" enforceable, not only displayed.
- **One transaction per claim**, four cases:
  - **new** (loaded, unverified): as today (admit the evidence as the human, bind, admit the claim).
  - **revision** (the current claim is challenged and a candidate exists for the current text): as the human, begin review, resolve as revised (with the note), close the old claim; then reopen a **successor** naming it as its predecessor; set its uncertainty explicitly (so it carries an uncertainty receipt like every other claim); admit the new evidence (human, with the note); bind it; admit the successor.
  - **reaffirm** (the current text matches evidence that is still admitted and bound to the challenged claim: a reverted edit, or a removed entry put back while its claim is still challenged): as the human, begin review and reaffirm.
  - **restored** (a successor reopened from a revoked or denied claim): as a new claim, with lineage. When the text is **unchanged**, the candidate already exists and is admitted, so there is no new evidence to admit; the human named by `--by` is then the actor on the **bind and the admit of the successor**, so the receipts still say who made it assertable again. When the text changed while the claim was revoked, the evidence follows the revision steps.
- **One note per run**, recorded on every receipt of the run.
- **The report** lists a claim as verified only after its transaction has committed, says per claim what succeeded and what was refused, and the exit code is non-zero if any claim was refused. A partial result is legal, because unverified revisions stay withheld.
- The **old evidence is left admitted**: it is an accurate record of what the source said then; revoking it would say it was wrong. (This is also why a revert can be reaffirmed.)

### 4.3 `revoke` (the human, final)

`glossary revoke --by human:NAME --note "..." (--term T | --anchor A | --all-removed) --confirm DIGEST`

- Refuses a non-human `--by`, an empty or placeholder note, and **any claim still in the sources** (a live claim is revised, never revoked).
- No default selection. `--anchor A` selects only among **removed** claims. `--confirm DIGEST` is computed the same way as for verify, over the exact claims, their state and the candidate id of the admitted evidence being retired, so a bad edit that deleted a section cannot be revoked in one careless run.
- One transaction per claim, reported per claim, the human as the actor. A challenged claim gets a review and then a revoke; an admitted claim that load has not yet reached is revoked directly; a claim that was **never verified** is **denied** (review, then reject) and reported as "denied (never verified)".
- **Claims only.** Terms, aliases, notes, groups and outside usages stay admitted but unused: they assert nothing, and revoking a term object would challenge every claim that uses it. Evidence stays admitted.
- It is the **only** thing in the loader that ever revokes.

### 4.4 `status`

Every claim in the sources lands in exactly one bucket, so the counts add up (this fixes today's negative "not loaded"):

| Bucket | Meaning | Store label |
|---|---|---|
| not loaded | new in the sources | (none yet) |
| drift | an edit was saved but not yet loaded | Admitted |
| loaded, unverified | a new claim | Pending Evidence |
| revision awaiting verification | the old claim is challenged, the new text pending | Challenged |
| awaiting reaffirm | a reverted edit or a put-back entry; the text matches admitted evidence | Challenged |
| restored, awaiting verification | back in the sources after a revoke or denial | Pending Evidence |
| verified | | Admitted |
| needs attention | a state the loader never produces | (as stored) |

A separate section, **removed from the sources**, groups claims that are in the store but no longer in the sources by term with their state: removed and withheld (challenged), never verified (pending). Revoked or denied claims are done and no longer listed. Each removed claim is named by its source anchor; where a new claim shares the anchor (a changed note) the report says it was replaced. A term removed while a collisions row still names it fails loudly, so the report says its collision rows must go first. `status` and the editor name the **next step** for each state (load, verify, revoke); readers of the store do not.

### 4.5 `define` and the lint hook

- `define` reuses the doctrine's **projection labels verbatim** (Admitted, Pending Evidence, Challenged, Revised, Revoked, Closed, Not Projectable) with a reason, one line per withheld claim: `<what>: <label> (<reason>)`. It lists only the **current claim** of each statement, with an "earlier versions: N" hint. A revoked or denied claim with no successor is still listed (it is the record). An **integrity failure** is the first line, as a fault to fix. It never instructs. "(not verified yet)" is retired.
- The **lint hook stays silent** about withheld claims (it only advises on what the store asserts) and keeps saying it is inactive when the store fails its integrity check.

## 5. The collisions table

Collisions ("must not be confused with") move from hard-coded lists in `glossary.py` (`COLLISIONS`, `OUTSIDE_USAGES`) into `CONTEXT-MAP.md`, one row per pair:

```
## Collisions

| Term | In | Must not be confused with | In | Why |
|---|---|---|---|---|
| Scope | Permission gate | Scope | CCGF hypergraph | a folder tree in the gate, an operational namespace in CCGF |
| Fast path | Permission gate | fast-path / diagnostic | outside: docs/ARCHITECTURE.md | a router route CCGF does not define |
```

- The first side is always a defined term. The second side is a defined term, or an **outside usage** marked `outside: <where>` in its "In" cell (never a Term; backed only by the map's own words).
- The evidence for each collision claim is its own row, byte for byte: editing one row changes one claim.
- The loader **fails loudly**, naming the section, when the section is missing or empty, a row does not have five cells, a row names an undefined glossary or term, or a pair appears twice in either order. A `|` or line break inside a cell is refused, and the "Why" cell is required and non-empty.
- The two prose bullets in `CONTEXT-MAP.md` that state collisions are trimmed so the table is the only statement. The "independent" relationship line stays, and so does the note that "Admission gate" belongs to CCGF (an avoid entry). **This edit is a draft; it is not made until the user says go.**

## 6. The editor

The term is the unit. v1's shell, term form and list are kept.

- **Header:** v1's chips, extended with the new counts (claims, verified, to load, to verify, removed and withheld).
- **Left:** the term list with a pill per term in the section 4.4 bucket names, and **Collisions** as its own item with a state pill.
- **A term's page:** the v1 term form (unchanged) above a **table of its claims**. Each row: the claim (expandable); its **state** as a pill; what the **store says** (projection label and the recorded reason from section 7, worded as `define` words it); the **next step**. Expanding a claim shows the case: a revision shows the old admitted text beside the new with changed words marked; a reaffirm shows "unchanged since verified on `<date>` by `<who>`"; a restored claim shows when it was revoked or denied, by whom and their note; a removed claim shows the admitted text being retired, who verified it and when; a drifted one shows the saved change against what the store still asserts; a claim still pending after a failed check shows "last check failed: `<reason>`" from the receipt the store already keeps. The collisions that name the term are listed below the table.
- **Remove term** is a button in the term's header. It opens an inline consequences box (no modal): the number of claims that will then be reported as removed, with Remove and Cancel; or, if a collisions row names the term, a plain-text **refusal**. It edits the Markdown only and never revokes.
- **Collisions screen:** a table of the pairs with a state pill per row and Add a pair.
- **"The database" panel** under the term page holds three inline sections: **Load** (the page runs it; it admits nothing), **Verify** (a count per case, one checkbox per term all ticked by default, the command builder) and **Revoke** (the removed claims, the same builder). The builder shows the selection, the **digest**, a name field and a note field with the section 4 rules, and a Copy command button that stays disabled until both are valid. **The page never runs verify or revoke.** There is no drawer.
- **Refresh:** on the Refresh button and when the window regains focus; no polling. After a run elsewhere the page shows each claim's "verified by `<name>` on `<time>`" from its receipts.
- The look is captured in the throwaway prototype `.scratch/glossary-editor/prototype/editor-v2-screens.PROTOTYPE.html` (variant C, with the inline panel).

## 7. The closed list of reasons

The machine reasons below are fixed strings, written once here, and are the **only** strings the loader records on its challenge, denial and successor receipts. Human notes are quoted verbatim. A new reason has to be added to this table on purpose.

| Situation | Label | Reason clause |
|---|---|---|
| New claim, loaded | Pending Evidence | loaded, not yet verified |
| Successor of a revoked or denied claim | Pending Evidence | restored, not yet verified (was revoked or denied on `<date>`) |
| Source text changed | Challenged | source text changed; revision awaiting verification |
| Removed from the sources | Challenged | no longer in the sources; awaiting revoke |
| Its evidence was revoked | Challenged | its evidence was revoked |
| A term it uses was revoked | Challenged | a term it uses was revoked |
| Revoked by a human | Revoked | revoked by `<name>` on `<date>`: `<their note, verbatim>` |
| Denied by a human, never verified | Not Projectable | denied by `<name>` on `<date>`, never verified: `<their note, verbatim>` |

## 8. Migration

The collisions table is the first thing to go through the revise path, in this order:
1. Build the loader changes (at least the id chain, load's challenge, verify's revision case, and the table parser).
2. Add the table to `CONTEXT-MAP.md` and trim the two prose bullets (with the user's go-ahead).
3. `load`: the **six** existing collision claims change evidence text (today two prose lines back them), so each is challenged and gets a candidate.
4. A human runs `verify` for the six with a **real note**. This also replaces the three outside-usage claims whose receipts carry the placeholder note `...` (that history stays; the new receipts say what was reviewed).

Nothing else migrates: the 139 avoid claims and the definitions keep their evidence as it is.

## 9. Deltas

**From editor v1 (`hypergraph-db/glossary-editor/`)**
- The claims table on each term's page; the case-grouped verify section with diffs; the removed-claims section with the revoke builder; the "The database" panel replacing v1's short database panel.
- The Remove term action and its refusal; the collisions screen; new pills and next-step lines; the projection label and reason on every claim.
- The command builders take a digest and the loader's name and note rules. v1's page-only checks stay as a convenience.
- Unchanged: the term form, the list and search, preview and save, the token/Host/Origin guards, the atomic write and the stale-file check.

**From the loader today (`glossary.py`)**
- Follow the id chain to find the current claim; the load-time candidate-plus-challenge step; load's challenge of removed claims; successor proposal from a revoked or denied claim.
- `verify`: explicit selection, `--confirm`, four cases, name and note rules moved in, non-zero exit on any refusal, report after commit.
- New `revoke` command (the only revoker).
- `status`: the partition and the "removed from the sources" section. `define`: per-claim lines, current claim only, the closed reasons.
- The collisions table parser replaces the hard-coded lists and the sentence matching.
- Two defects fixed by construction: `status` printing a negative "not loaded" count; `verify` listing a claim as both verified and refused when its transaction rolls back.

## 10. Limits, dependency and notes

- **The store does not enforce the machine/human split.** A `sys:` actor can revoke with an empty note; the loader's command is the only gate. Enforcing it in the store (for example with refusal-only triggers) is a possible later hardening and is not part of v2.
- **Cross-repo dependency.** The editor lives in `chi` (the Markdown does) but imports `chi-platform` code and runs its loader. It finds it through `CHI_GATEWAY_DIR` (default `~/Projects/chi-platform/infra/chi_agent_gateway`). Revisit if the gateway's API shifts.
- **Performance** (measured on scratch stores of 267 to 4,267 claims): load is linear at about 2.5 ms per claim; the integrity check is linear (0.96 s at 4,267 claims); foreign keys are enforced and 8 foreign-key columns have no index, harmlessly (the append-only triggers forbid parent-key changes). Two notes only: reuse one connection in the evidence insert if a rebuild ever feels slow (the insert re-runs `init_db()` and opens a connection per claim, about 43% of load); and watch the per-call integrity cost in the lint hook past roughly 10,000 claims (`define` and `lint` each re-run the whole check).
- **What is unverified:** the loader changes are designed from the store facts in `.scratch/glossary-editor/research/02-store-lifecycle-facts.md`, confirmed by simulation on scratch stores, not built. Concurrent writers and a real process kill were not exercised.

## 11. Settled at review

The five points below were open when the spec was first written; the user accepted the recommendations on 1 to 4 and, on 5, asked for **Withheld** to be included in the drafts.

1. **A restored claim whose text is unchanged.** Settled: the human is the actor on the bind and the admit of the successor (section 4.2 and the table in section 3).
2. **`--anchor` is not unique.** Settled: `revoke` selects only among removed claims and `verify` only among pending or challenged ones; the digest covers claim ids (sections 4.2 and 4.3).
3. **The hypergraph web view.** Settled: out of scope for v2; it stays a snapshot (section 2).
4. **How v2 is tested.** Settled: the v1 practice extended, on scratch stores only, with a sabotage probe per safety rule (the digest, the human-only refusal, the live-claim refusal, the machine-only-less-assertive rule, resumability after a crash between the candidate and the challenge), the status partition asserted to sum to the total, and the editor's new screens checked in Chrome on scratch copies. The cases are in section 12.
5. **The proposed glossary and doctrine text** ([proposed-glossary-terms.md](proposed-glossary-terms.md)) The user asked for **Withheld** to be included with **Successor**, **Predecessor**, **Outside usage** and **Drift**, and on 2026-09-20 gave the go-ahead to apply the glossary entries: **the five entries were applied** to `docs/ccgf/CONTEXT.md` (not yet loaded into the hypergraph). The doctrine paragraph in that file stays **proposed, not applied**, and so does the `CONTEXT-MAP.md` edit (the collisions table); each needs its own go-ahead. Rename as one act stays out of scope (section 2).

## 12. Build slices (a suggestion) and test cases (the agreed approach)

Slices, each shippable on its own: (1) the id chain and the `status` partition with the removed section (read-only); (2) load's challenge for changed and removed claims; (3) `verify` with selection, digest, the four cases and the name and note rules; (4) `revoke`; (5) the collisions table parser and the migration in section 8; (6) `define` and the closed reasons; (7) the editor screens.

Cases to test (each against a scratch store): a changed definition is challenged at load and withheld; load is resumable after a crash between the candidate and the challenge; editing twice leaves a stale candidate that is never bound; verify refuses with no selection or a wrong digest, and the digest changes with the text, the selection and the case; a revision creates a successor with the predecessor and an uncertainty receipt; a reverted edit is reaffirmed; a dropped alias is withheld and revoke refuses a live claim; a never-verified removed claim is denied; a claim put back after a revoke returns as a successor; `status` counts always sum to the total; only strings from section 7 appear on receipts; `define` lists current claims only; the page never runs verify or revoke; Remove term refuses while a collisions row names the term.

## 13. Decision index

| Decision | Where |
|---|---|
| Destination, scope, standing rules | [Charting decisions](../../.scratch/glossary-editor/issues/01-charting-decisions.md) |
| What the store allows (actors, reopen, atomicity) | [The store's lifecycle facts](../../.scratch/glossary-editor/issues/02-store-lifecycle-facts.md), [findings](../../.scratch/glossary-editor/research/02-store-lifecycle-facts.md) |
| Revise: classes, load, verify cases, buckets | [Revise mechanics](../../.scratch/glossary-editor/issues/03-revise-mechanics.md) |
| Removal, revoke, deny, restoring | [Removal and revoke](../../.scratch/glossary-editor/issues/04-removal-and-revoke.md) |
| The collisions table | [Collisions list](../../.scratch/glossary-editor/issues/05-collisions-list-format.md) |
| The digest guard, selection, notes | [The verify panel](../../.scratch/glossary-editor/issues/06-verify-panel-source-text.md) |
| The screens | [Editor v2 screens](../../.scratch/glossary-editor/issues/07-editor-v2-screens.md) |
| What readers say, the closed reasons | [What readers say about a withheld term](../../.scratch/glossary-editor/issues/09-what-readers-say-about-a-withheld-term.md) |
| Draft glossary and doctrine text (not applied) | [proposed-glossary-terms.md](proposed-glossary-terms.md) |
