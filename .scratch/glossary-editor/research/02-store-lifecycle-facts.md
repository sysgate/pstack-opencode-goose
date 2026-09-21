# The store's lifecycle facts: what a changed or removed claim may do

Ticket: `issues/02-store-lifecycle-facts.md`. Read-only research; nothing edited. Scratch runs used copies of the glossary files and fresh stores made with `python3 -m app.hypergraph.migrations migrate --db <scratch> --create` (`PYTHONPATH=.` from the gateway dir); the real prototype database was not opened.

Notation. `GW` = `/Users/robertlai/Projects/chi-platform/infra/chi_agent_gateway/app`; `H/` = `GW/hypergraph/`. "**DB**" = enforced by a SQL trigger in `H/migrations.py` (holds even for code that bypasses Python). "**Py**" = enforced only by a Python function. "**Doctrine**" = `AGENTS.md` / `docs/ARCHITECTURE.md` (section 7 and 9.2). "**Sim**" = confirmed by running library code on a scratch store. Vocabulary: term, claim (hyperedge), revoke.

## Headline answers to the map's assumptions

1. **A machine actor MAY challenge an ADMITTED claim, if it is `sys:`. It may NOT if it is `adapter:` or `gen:`.** `revision.challenge` calls `require_governance` (H/revision.py:30), and governance kinds are `sys` and `human` (H/actors.py:8,16-22). Sim: `adapter:glossary-md` and `gen:x` were refused with `GENERATION_CANNOT_ADMIT`; `sys:adjudicator` succeeded (ADMITTED to CHALLENGED). Tests: `tests/test_hypergraph_bindings.py:775-811`.
2. **The store does NOT confine revoke, reaffirm or admit to humans.** `sys:` may also revoke a term (H/objects.py:172-187), revoke evidence (H/evidence.py:111-128), revoke a claim (H/admission.py:79-98), begin review, resolve a review as reaffirm, revise or close, and admit a claim or a term. Only three acts are human-only: verifying tier-3 evidence (Py evidence.py:74; DB trigger `evidence_records_born_admitted`, migrations.py:197-199), granting an ambiguity allowance (DB, migrations.py:518-527), and voiding a `CONTRADICTS` binding (DB, migrations.py:621-622). The map's rule "only a human makes it final (revoke)" is therefore an editor-side policy, not something the store enforces.
3. **Reopen creates a NEW claim with predecessor lineage. It never resumes the old one.** New id `he_...`, state `PENDING`, `predecessor_ids = [old id]`, `lineage_hash` set, no evidence bindings carried over. Sim confirmed; details in section 2.
4. **A revise is atomic only if the caller puts every step in ONE `write_transaction`.** Each library function needs an open transaction and does not open one itself, so a chain of challenge, begin-review, revise, close and reopen is atomic when wrapped (Sim F: a crash before commit left state `ADMITTED` and all counts unchanged). Nothing in the store or the loader today does this for you. The candidate-evidence insert cannot join that transaction from another connection (section 5).
5. **Reopen only works from a terminal claim.** Terminal = `DENIED`, `REVOKED`, `CLOSED` (H/states.py:10). A `REVISED` claim is not terminal: `reopen` refused it with `PREDECESSOR_NOT_TERMINAL` (Sim I). So the revise path must run through `CLOSED` first.
6. **The loader cannot see a reopened successor.** Its claim id is computed with no predecessors (H/glossary.py:236), and a successor's id includes its predecessor, so `status`, `load` and `verify` keep looking at the old, now-`CLOSED` claim (Sim A, section 4).

## 1. Legal state transitions

The nine states, the terminal set and the legal table are one frozen table shared by claims and terms: `H/states.py:7-22`, `docs/ARCHITECTURE.md` section 7, `AGENTS.md:430-441`. Doctrine and code agree; a test compares Python to SQL. Both semantic objects (`semantic_objects`, migrations.py:135-153) and hyperedges (migrations.py:322-340) carry the same 14-row `CHECK`-style trigger `*_legal_transition`; `DENIED`, `REVOKED`, `CLOSED` have no outgoing row.

### 1a. Claims (hyperedges)

Receipt column: what the DB requires to be the LATEST receipt on the claim, and that its `basis` names the move (`from`, `to`) (`hyperedges_receipt_names_the_move`, migrations.py:442-450; it exempts CANDIDATE and PENDING to PENDING). "Actors" is what the Python entry point allows (the DB checks no actor kind on claim moves; the receipt's `actor` need only be non-empty, migrations.py:68).

| Move | DB guard (migrations.py) | Receipt (type/decision) | Py entry point and actors |
|---|---|---|---|
| CANDIDATE to PENDING | `hyperedges_signature_at_ingestion` 345-389 (roles legal and required) | none | `hyperedges.propose` (H/hyperedges.py:82-141): anyone; members must be ADMITTED terms |
| PENDING to PENDING | legal_transition only; exempt from names_the_move | none required; a failed boundary writes a PEND receipt of that boundary's type | `admission.admit` on boundary failure (H/admission.py:57-61): governance |
| PENDING to ADMITTED | 394-410 (HYPEREDGE_ADMIT/ADMIT latest, `receipt_id` sealed to it); 636-666 (every member ADMITTED; counting SUPPORTS binding; no counting CONTRADICTS; confidence bound present) | HYPEREDGE_ADMIT / ADMIT | `admission.admit` (H/admission.py:48-70): `sys:` or `human:` |
| PENDING to UNDER_REVIEW | 420-426 | REVISION_OPEN / PEND or UNCERTAINTY_BOUND / PEND | `revision.begin_review` (H/revision.py:37) or `admission.admit` on 幅界 failure: governance |
| PENDING to DENIED | 428-437 | REVISION_CLOSE / DENY | no dedicated Py function (only `revision.justify_and_move`, 16-23); `resolve_review("reject")` needs UNDER_REVIEW |
| ADMITTED to CHALLENGED | 412-418 | REVISION_OPEN / PEND | `revision.challenge` (H/revision.py:26-34): `sys:` or `human:`; reason required |
| ADMITTED to REVOKED | 428-437 | REVISION_CLOSE / REVOKE | `admission.resolve_review("revoke")` (H/admission.py:79-98): governance; reason NOT required (`note=""` default) |
| CHALLENGED to UNDER_REVIEW | 420-426 | REVISION_OPEN / PEND | `revision.begin_review`: governance |
| UNDER_REVIEW to ADMITTED (reaffirm) | 394-401 (REVISION_CLOSE/ADMIT latest) plus the four boundary triggers 636-666 | REVISION_CLOSE / ADMIT | `resolve_review("reaffirm")`: governance; needs a HYPEREDGE_ADMIT in history; re-runs `boundaries.check` |
| UNDER_REVIEW to REVISED | 428-437 | REVISION_CLOSE / REVISE | `resolve_review("revise")`: governance; needs admission history |
| UNDER_REVIEW to PENDING (re-run) | 452-458 | REVISION_CLOSE / PEND | `resolve_review("rerun")`: governance; only if never admitted |
| UNDER_REVIEW to DENIED | 428-437 | REVISION_CLOSE / DENY | `resolve_review("reject")`: governance; only if never admitted |
| UNDER_REVIEW to REVOKED | 428-437 | REVISION_CLOSE / REVOKE | `resolve_review("revoke")` |
| REVISED to CLOSED | 428-437 | REVISION_CLOSE / REVISE | `revision.close` (H/revision.py:45): governance |

Sim B: `resolve_review("revoke")` succeeded from ADMITTED; from CHALLENGED it raised `ILLEGAL_TRANSITION: CHALLENGED -> REVOKED` (a challenged claim must go through UNDER_REVIEW first). PENDING to REVOKED is also not in the table. Which path a claim took to UNDER_REVIEW cannot be read from state; `revision.was_admitted` reads the receipts (H/revision.py:54-56).

Ordering rule (Py): every move goes through `revision.justify_and_move` (16-23): append the receipt first, then move. If the move is illegal the receipt has already been appended in the open transaction, so the caller's rollback is what removes it (`tests/test_hypergraph_bindings.py:807-811`). A caller that catches `Refused` inside the transaction and carries on would leave a stray receipt (reading; not simulated).

### 1b. Terms (semantic objects)

Same table. Differences: a term reaches ADMITTED by 名界 alone and is born with no DSN state.

| Move | DB guard | Receipt | Py entry point and actors |
|---|---|---|---|
| (insert) CANDIDATE | `semantic_objects_born_candidate` 119-122 | none | `objects.propose_candidate` (H/objects.py:67-96): anyone; predecessors must be terminal |
| CANDIDATE to PENDING | legal_transition | none | inside `propose_candidate` |
| narrow (DSN outcome; PENDING to PENDING, UNDER_REVIEW or DENIED) | legal_transition | DSN_COMMIT / CLEAR, BOUND, PEND or DENY (Py-only) | `objects.narrow` (99-152): **no governance check at all**; the `actor` is only recorded (the loader passes `adapter:glossary-md`) |
| PENDING to ADMITTED | `semantic_objects_admission_needs_receipt` 157-163 (any SEMANTIC_ADMIT on the subject) | SEMANTIC_ADMIT / ADMIT | `objects.admit` (155-169): governance; DSN state must be NARROWED or BOUNDED_AMBIGUOUS |
| ADMITTED to REVOKED | legal_transition **only: no receipt trigger** | REVISION_CLOSE / REVOKE, appended by Py; integrity reports `REVOKED_WITHOUT_RECEIPT` if missing (H/integrity.py:196) | `objects.revoke` (172-187): governance; reason required |
| ADMITTED to CHALLENGED, UNDER_REVIEW and onward | legal in the table | **UNSETTLED** | No Py function moves a term through CHALLENGED, REVISED or CLOSED. Only `revoke` and the CONFLICT to UNDER_REVIEW narrowing (149) are wired. |
| ADMITTED with BOUNDED_AMBIGUOUS to NARROWED (re-narrow) | `narrow` allows it in state ADMITTED (131-132) | DSN_COMMIT / CLEAR | governance not required; triggers `bindings.revalidate` on live claims (142-144) |

### 1c. Candidate evidence (`candidate_evidence`, the gateway's table)

Guards are refusal-only triggers named `hypergraph_*`, with UPDATE and DELETE only, so the gateway's own INSERT is never blocked (migrations.py:212-258, rules at 1-14). Legal: CANDIDATE to ADMITTED, CANDIDATE to DENIED, ADMITTED to REVOKED (212-219). DENIED and REVOKED are terminal; a retry is a new candidate (doctrine `AGENTS.md:391`, `ARCHITECTURE.md` section 9.2).

| Move | DB guard | Receipt | Py entry point and actors |
|---|---|---|---|
| CANDIDATE to ADMITTED | 222-228 (an `evidence_records` row with the same receipt id) and `evidence_records_born_admitted` 186-200 (kind `tool_output`; hash equals the candidate's; EVIDENCE_ADMIT/ADMIT sealing the hash; tier 3 needs `actor LIKE 'human:%'`) | EVIDENCE_ADMIT / ADMIT | `evidence.admit` (H/evidence.py:60-92): governance, and `human:` for tier 3 (Py line 74 plus DB) |
| CANDIDATE to DENIED | 230-237 | EVIDENCE_ADMIT / DENY | `evidence.deny` (95-108): governance; reason required |
| ADMITTED to REVOKED | 239-245 (any REVISION_CLOSE/REVOKE receipt on the subject) | REVISION_CLOSE / REVOKE | `evidence.revoke` (111-128): governance (`sys:` allowed); reason required |
| body, hash, kind, source, provenance | immutable, 251-254; never deleted, 256-258; `admission_receipt_id` set once, 247-248 | | |

The evidence record is immutable and never deleted (migrations.py:203-208). The candidate id in the glossary loader hashes `[uri, anchor, text]` (H/glossary.py:217-219), so changed source text means a different candidate id.

## 2. What revoke, reopen and void do

| Act | Rows changed | New ids | Receipts |
|---|---|---|---|
| **Revoke a term** (`objects.revoke`) | term row `ADMITTED` to `REVOKED`, `updated_at` | none | one REVISION_CLOSE/REVOKE on the term (`basis {reason}`); then cascade receipts below |
| **Revoke a claim** (`resolve_review "revoke"`) | claim state `REVOKED` | none | one REVISION_CLOSE/REVOKE on the claim (`basis {outcome, note, was_admitted, from, to}`). No cascade to terms, evidence or bindings; allowances tied to it lapse lazily (H/bindings.py:24,49-50) |
| **Revoke evidence** (`evidence.revoke`) | candidate `ADMITTED` to `REVOKED` | none | REVISION_CLOSE/REVOKE on the candidate; then cascade below |
| **Void a binding** (`bindings.void`, `_void`; H/bindings.py:163-186) | `hyperedge_evidence.void_reason`, `voided_receipt_id` set once (DB 608-612); row never deleted (626-628) | none | REVISION_CLOSE/REVISE on the CLAIM, `basis {binding_voided, reason}`. Void of a `CONTRADICTS` binding needs `human:` (Py 176-177; DB 621-622). Nothing in the trigger checks the claim's state, so a binding on a `CLOSED` claim can be voided (Sim: evidence revoked after close voided the old binding) |
| **Reopen a claim** (`hyperedges.reopen`, H/hyperedges.py:144-152) | inserts a new claim and its members | new `he_` id | none (a proposal writes no receipt); the new claim is `PENDING` |
| **Reopen a term** (`objects.reopen`, H/objects.py:190-194) | inserts a new term | new `so_` id | none; the new term is `PENDING` with no DSN state and must be narrowed and admitted again |

**Reopen, exactly (Sim A, confirmed).**
- Requires every named predecessor to be in `DENIED`, `REVOKED` or `CLOSED` (Py: hyperedges.py:122-126, objects.py:81-85; DB-side backstop is the integrity check `PREDECESSOR_INVALID`, integrity.py:239, not a trigger).
- The new claim copies relation type, scope, `valid_from`, `valid_to`, members, `confidence_bound` and `uncertainty_notes`. In Sim the copy had confidence 1.0 and the "the claim is that the source states this" note but **no UNCERTAINTY_BOUND receipt**: the receipt trigger only fires on UPDATE (migrations.py:676-683), so the copy at INSERT has none. Integrity reported no problem. Bindings are not carried over (F7, hyperedges.py:9,146-147): the new claim must be bound and admitted again.
- `id = "he_" + sha256(canonical{relation_type, scope, sorted members, valid_from, valid_to, sorted predecessor_ids})[:16]` (hyperedges.py:29-35). Terms: `so_` over `{text, scope, source_context, predecessors}` (objects.py:31-33). The same members and text reopened again after a terminal state get a NEW id only because the predecessor is in the hash; without a predecessor the id already exists and `propose` refuses with `DUPLICATE_CANDIDATE` (hyperedges.py:128-129).
- `predecessor_ids` is canonical JSON of the sorted, de-duplicated list, e.g. `["he_d0dbc7da8e77ed07"]`. `lineage_hash = ""` when there are none, else `sha256(canonical [[pred_id, id of that predecessor's LATEST receipt], ...])` (hyperedges.py:72-79; objects.py:57-64). Sim: matched `payload_hash([[old, receipt of the CLOSED move]])`. Both columns are immutable after insert (DB 130, 308-310). A claim may name predecessors whose members differ from its own; only terminality is checked (reading of hyperedges.py:122-126).
- Doctrine agrees: a reopened claim or term "starts a new `CANDIDATE` that names the earlier one in its `predecessor_ids`; the earlier one is never resumed" (`ARCHITECTURE.md` section 7; `AGENTS.md:441`). The doctrine also says the id "includes its predecessors, so identical content raised again gets a new id".

**Cascades (Py, all by the actor passed in; a cascade uses the same actor).**
- Revoke evidence (`bindings.void_for_evidence`, H/bindings.py:244-261): every un-voided binding of that evidence record is voided (SUPPORTS always; CONTRADICTS only if the actor is `human:`, otherwise left, it "no longer counts" because its evidence is not ADMITTED). Then `settle` per claim (227-241): with no counting support left, a `PENDING` claim gets an EVIDENCE_ADMIT/PEND receipt `UNSUPPORTED` and stays `PENDING`; an `ADMITTED` claim is challenged (REVISION_OPEN/PEND, `support lost: UNSUPPORTED`) and becomes `CHALLENGED`; any other state is left alone. Sim B: the claim went `CHALLENGED`, receipts on the claim were REVISION_CLOSE/REVISE (void) then REVISION_OPEN/PEND (challenge), integrity clean. Doctrine matches (`ARCHITECTURE.md` section 9.2; `AGENTS.md:395`).
- Revoke a term (H/objects.py:181-186): for every claim using it in `PENDING`, `ADMITTED`, `CHALLENGED` or `UNDER_REVIEW`, allowances are revalidated, and an `ADMITTED` claim is challenged (`member X revoked`). `PENDING` claims stay `PENDING` (they will fail 名界 at admission). Sim C: a term used by 5 claims left all 5 `CHALLENGED`. Nothing cascades to evidence.
- Revoke or revise a claim: no cascade.

## 3. Challenge and under review

- **Challenge** (`revision.challenge`, H/revision.py:26-34): governance actor (`sys:` or `human:`), non-blank reason, claim must be `ADMITTED`; appends REVISION_OPEN/PEND with `basis {reason, from: ADMITTED, to: CHALLENGED}`, then moves. DB requires that receipt as latest (migrations.py:412-418). The claim leaves projection at once (only `ADMITTED` is assertable, H/projection.py:39-40). Sim A: `define` on the term went from asserting the definition to "1 withheld" and no definition.
- **Under review** (`revision.begin_review`, H/revision.py:37-42): governance; from `CHALLENGED` (or `PENDING`); REVISION_OPEN/PEND with `basis {review: begun, from, to}`. From `ADMITTED` directly it is illegal, so a review of an admitted claim is two moves and two receipts (challenge, then begin_review). They can share one transaction.
- **Actor kinds** (H/actors.py:1-22, docstring "Only the sys ... and human kinds are governance; gen (a model) and adapter (an extractor) may propose but never decide"): `sys:` and `human:` pass; `adapter:` and `gen:` are refused with `GENERATION_CANNOT_ADMIT`. The check is the kind only, so `sys:glossary-editor` would pass as much as `sys:adjudicator`; `sys:adjudicator` is defined as "acts for cascades no person decided" (actors.py:9). The check is Py-only: `receipts.append` accepts any non-empty actor string (receipts.py:59-60).
- **Doctrine on actor kinds**: `AGENTS.md:849-870` (adapters translate to candidates, "do not admit knowledge") and `ARCHITECTURE.md:498`. The doctrine text I found does not name which kinds may challenge; that split is stated in code (actors.py) and tests only. The map's "a machine may only make the store less assertive" is consistent with challenge-by-`sys:`, but is not the rule the code implements (see headline 2).
- The three loader actors: `adapter:glossary-md` (narrowing and `proposed_by`), `sys:adjudicator` (admits terms and claims, sets uncertainty, binds), human passed by `--by` (verifies) (H/glossary.py:40).

## 4. What today's glossary loader does, step by step, and what it never does

Loader: `H/glossary.py`. All loops run over `plan.claims` / `plan.objects`, i.e. what the sources say now (302, 341, 374).

- **plan** (`build_plan`, 143-211): pure; parses both glossaries and the map; supports `overrides={path: text}`; ids derive from the path, so real paths must be kept (144-145).
- **load** (265-323), machine phase:
  1. `require_migrated` (read). 2. For each term/object not yet in the store: one `write_transaction` doing `propose_candidate`, `narrow` (`adapter:glossary-md`, DSN_COMMIT/CLEAR, basis kind `source`), `admit` (`sys:adjudicator`, SEMANTIC_ADMIT) (283-289). Existing objects are skipped, never updated. 3. One request receipt per source file and sha256 if absent, via `record_request` on a **separate connection** (296-300; state `NOT_EVALUATED`). 4. For each claim: if the claim id exists, skip it, and **if its candidate id is missing count `drift` and leave it alone** (304-307); else insert the candidate evidence on a **separate connection** if absent (310-313), then in one `write_transaction`: `hyperedges.propose` (`PENDING`, no receipt) plus `admission.set_uncertainty` (UNCERTAINTY_BOUND/BOUND by `sys:adjudicator`, confidence 1.0) (318-321).
  - Idempotent: a second load changed nothing (Sim: all zeros). Claim ids do not include the text (`_hyperedge_id` uses `()` predecessors, 231-236); candidate ids do (217-219). Hence a text edit yields the same claim id and a new candidate id: drift.
  - Sim A: after editing one definition, `load` reported `{requests: 1, drift: 1, candidates: 0, hyperedges: 0}`. It recorded a new request receipt for the new file hash but inserted **no candidate** for the new text and proposed nothing.
- **verify** (329-366), human phase: needs `human:` and a non-blank note (335-338). Per claim: skip if claim or candidate missing (drift if the claim exists but the candidate for THIS text does not); skip if `ADMITTED`; else in **one `write_transaction` per claim**: `evidence.admit` (human, EVIDENCE_ADMIT/ADMIT; only if the candidate is `CANDIDATE`), `bindings.bind SUPPORTS` (`sys:adjudicator`, `proposed_by=adapter:glossary-md`), `admission.admit` (`sys:adjudicator`) (354-363). A boundary failure is recorded, not raised, so it commits with the claim `PENDING` or `UNDER_REVIEW`. A `Refused` rolls that claim back. Reporting quirk (reading): `out["verified"]` is appended at 357 before the transaction commits, so a claim rolled back later in the same block is listed as both verified and refused.
- **status** (372-390): counts loaded, drifted, verified, admitted, pending. Only `ADMITTED` and `PENDING` are broken out; a `CHALLENGED`, `CLOSED` or `REVOKED` claim counts as loaded and verified but as neither. Observed: with one claim drifting, `claims_not_loaded` came out **-1** (it is `claims - loaded - drift`, and a drifted claim is already in `loaded`).
- **define / lint** (408, 505): read-only, `ADMITTED` claims that pass the integrity check only; a claim that is not assertable is counted as `withheld` and never shown.

**Never does (reading of the loops plus Sim):**
- never revokes, challenges, revises, closes, denies, voids, or reopens anything; never writes a `REVISION_*` receipt.
- never detects removal: a term or claim that is in the store but no longer in the sources is never visited (loops are over the plan). Its `ADMITTED` claim keeps being asserted by `define` until someone revokes it.
- never inserts a candidate for changed text (it skips at 304-307), so `verify` can never bind or admit new text on an existing claim; `verify` reports it as `drift` forever.
- never updates an existing term, candidate or claim; never runs migrations (259).
- never sees a successor claim. Sim A: after challenge, revise, close and `reopen`, the loader's id for that anchor is still the old `CLOSED` claim; `load` proposed nothing; `verify` reported `refused: ['Permission gate/definition: NOT_PENDING: CLOSED']` on every run. The successor is invisible to `status`.
- Sim (end to end, scratch): challenge, begin review, revise, close, `reopen`, then `evidence.admit` a new candidate, `bind`, `admission.admit` on the successor: the successor reached `ADMITTED`, integrity clean, and `define` asserted the new text. It still reported "1 claim withheld" for the term because the `CLOSED` predecessor counts as non-assertable.
- Sim: revoking the OLD evidence after the close (`sys:adjudicator`) worked and voided the old binding; whether to do so is UNSETTLED (below).

## 5. Atomicity and what a crash leaves behind

Mechanics. `db.connect()` gives autocommit connections; `write_transaction` is `BEGIN IMMEDIATE`, rollback on any exception including `BaseException`, `COMMIT`, then the anchor sidecar is appended after the commit (H/db.py:22-33; anchor.py:114-126, which never raises). Every library function raises `OPERATION_OUTSIDE_TRANSACTION` if no transaction is open.

| Operation | Transaction | What is atomic |
|---|---|---|
| each new term (loader 283-289) | one `write_transaction` per term | propose, narrow, admit together |
| request receipt (`record_request`) | **separate connection** (`ledger._connect`, own commit; GW/ledger.py:121-154) | its own row only; no receipt-chain entry |
| candidate evidence insert (`ledger.insert_candidate_evidence`, GW/ledger.py:223-257) | **separate connection**, `init_db()` then `with _connect()`, commits at once | its own row only |
| each new claim (loader 318-321) | one `write_transaction` | claim, members, uncertainty receipt together |
| verify, per claim (354-363) | one `write_transaction` | evidence admit, binding, claim admit together |
| challenge, review, revise, close, reopen, revoke, void, cascades | whatever transaction the caller opened | the library never opens one; a caller can put a whole revise chain in one |

Facts from Sim:
- **D. Crash between the candidate insert and the claim transaction** (fault raised in `hyperedges.propose` on the first claim): the store then had 229 terms, 3 request receipts, **1 candidate in `CANDIDATE`, 0 claims**, 458 receipts. Integrity reported no problem and no warning; `status` shows nothing loaded. A rerun of `load` reused the orphan candidate (`candidates: 266, hyperedges: 267`) and completed. So the state is benign and self-healing for the loader. A crash between two terms leaves a prefix of whole terms; a crash after the request receipt leaves an unused request receipt.
- **E. Crash inside verify's per-claim transaction** (fault after `evidence.admit`): rolled back fully, 0 candidates `ADMITTED`, receipt count unchanged; a rerun verified all 267.
- **F. Whole revise chain in one transaction with a crash before commit:** claim still `ADMITTED`, all table counts unchanged.
- **G. Same chain split across transactions** (challenge committed, then a stop): the claim stays `CHALLENGED`, integrity clean, `define` withholds it, and `verify` reports it `refused` (it cannot rebind a non-`PENDING` claim). The half-done state is legal and withheld, not corrupt.
- **The insert cannot simply be moved inside the hypergraph transaction from its own connection.** Sim: `ledger.insert_candidate_evidence` called inside `write_transaction` raised `OperationalError: database is locked` after 5.2 s (the `BEGIN IMMEDIATE` holds the write lock; the busy timeout is 5000 ms, GW/ledger.py:58). Doing the INSERT with the same connection inside the transaction works and rolls back with it (Sim: same-connection `INSERT INTO candidate_evidence` rolled back on error and committed with the transaction). The DB triggers on `candidate_evidence` never block INSERT (migrations.py:8-9). Whether a same-connection insert is acceptable to the gateway's design is UNSETTLED (the loader's comment says it is "inserted through the gateway's own insert path").

## 6. Unsettled

1. **Which `sys:` name the editor should act as.** `sys:adjudicator` is defined for "cascades no person decided"; a distinct `sys:glossary-editor` would also pass `require_governance`. The code does not prefer either.
2. **Who may revoke.** The store lets `sys:` revoke terms, claims and evidence and lets a claim be revoked with an empty `note` (`resolve_review` has no reason check). The map wants revoke to be human-only and to carry a reason; that is not enforced anywhere but the editor.
3. **Should the old evidence be revoked when a claim is revised?** The library allows it after the close (Sim) and it voids the old binding, but no doctrine text says it should happen. Leaving it means old, still-`ADMITTED` evidence for text no longer in the source.
4. **What the loader should do to see a successor** (its id has predecessors; it currently computes `()`), and how `status` and `verify` should treat a `CLOSED` predecessor. Not specified by any source.
5. **Terms and revise.** No Py function moves a term through `CHALLENGED`, `REVISED` or `CLOSED`, and the term's only receipt-less transition is `ADMITTED` to `REVOKED` (Py-only receipt). A changed term LABEL therefore means a new term (reopen or new), and a new claim naming the old one as predecessor; whether the old term is revoked is not decided.
6. **The doctrine names no rule for which actor kinds may challenge.** Only actors.py and its tests do.
7. **Same-connection candidate insert** into the gateway's table inside a hypergraph transaction (section 5): possible, but the gateway's stated design and any concurrency effect on a live gateway are not settled by these sources. (Nothing here ran against a live gateway.)
8. **Reopened claim's confidence.** It is copied and stored without an UNCERTAINTY_BOUND receipt; whether that is intended or a gap is not settled by the sources (integrity accepts it).
9. **Not run:** concurrent writers (a second connection during a hypergraph transaction beyond the 5 s lock test), and a real process kill (`kill -9`); the crash cases used raised exceptions inside the transaction, which follow the same SQLite rollback path (reading, `db.py:26-29`).

Sim scripts, if needed to reproduce: `/private/tmp/claude-501/-Users-robertlai-Projects-chi/5c3b4590-3e3f-42ee-92b4-702df1757dd7/scratchpad/sim1.py` to `sim5.py` (scratch only).
