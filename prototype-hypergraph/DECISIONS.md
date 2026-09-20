# Decisions on the prototype's findings

Recorded as they are made. **Decisions 1, 5 and 6 were applied to the prototype code on 2026-09-19 (the others already matched it), and all seven were applied to the doctrine on 2026-09-20** (`ARCHITECTURE.md`, the four `AGENTS.md` copies, the glossary). Each decision names the finding in `FINDINGS.md` it settles.

## 1. Receipt vocabulary (F1, F2): decided 2026-09-19

Add three receipt types and one decision value.
- **New receipt types:** `SEMANTIC_ADMIT` (semantic admission, 名界), `UNCERTAINTY_BOUND` (幅界), `REVISION_OPEN` (a challenge or review begins). Every boundary and every admission then has its own type.
- **New decision value:** `CLEAR`, meaning "passed this stage, not yet admitted". A narrowed term's DSN receipt uses `CLEAR`, not `ADMIT`.
- **Unchanged, but now stated:** `PEND` means "halted without denying" (including a challenge or review opened). `BOUND` means "a bound was recorded", which covers bounded ambiguity, an ambiguity allowance and an uncertainty envelope: one meaning, previously implicit.
- **Rejected:** keeping `ADMIT` for a narrowed term (the ledger would still read like an admission); splitting `PEND` into `HALT` and `OPEN` (the receipt type already carries the distinction).

## 2. Where meanings and the narrowing basis live (F3): decided 2026-09-19

Fields on the object. `SemanticObject` gains `meanings` (the finite set of remaining meanings) and `narrowing_basis` (what the narrowing rested on, with the alternatives considered), next to the existing `dsn_state`. They are the object's current values, as `dsn_state` is; the history of every change stays in the `DSN_COMMIT` receipts. This is what the prototype already does, and the allowance check reads them on every binding.
- **Rejected:** receipts only (every read and every allowance check would need a receipt lookup, and meanings would live apart from `dsn_state`); a separate `narrowing_records` table (another table and join for a handful of fields).

## 3. What goes into a deterministic id (F5): decided 2026-09-19

The source, not the result. An object's id is a hash of its source (original text, scope, source context) plus its predecessor ids. Narrowing changes its label, type and meanings but not its id, so every hyperedge that names it keeps working when a bounded term is later narrowed. A hyperedge's id hashes its relation type, scope, members with roles, validity and predecessors. Identical text raised again after a denial gets a new id only because it names a predecessor.
- **Rejected:** hashing the narrowed result (same meaning across sources dedupes, but narrowing an admitted bounded term would change its identity and force every hyperedge to be re-pointed); an assigned random or sequential id (breaks the promise of deterministic, reproducible rebuilds).

## 4. An admitted hyperedge loses its support (F6): decided 2026-09-19

It is CHALLENGED. This corrects my ambiguity-allowance walk-through, which said the hyperedge "returns to PENDING". A hyperedge still PENDING stays PENDING with `UNSUPPORTED` recorded. An ADMITTED one becomes CHALLENGED (reason `UNSUPPORTED`, receipt `REVISION_OPEN`), is withdrawn from projection at once, and goes through review like any other challenge. The state machine gains no new edge.
- **Rejected:** an `ADMITTED -> PENDING` edge (an admitted claim would leave the admitted state with no challenge or review); revoking on lost support (revocation is terminal, and the evidence may be re-bound under a narrower allowance).
- **Follow-up when the doctrine sync resumes:** the walk-through row in `docs/ccgf/proposed-ambiguity-allowance.md` still shows the wrong outcome; the applied doctrine text does not repeat it.

## 5. Dismissing a contradiction and voiding bindings (F9): decided 2026-09-19

A binding is never deleted. It is voided with a reason and a `REVISION_CLOSE` receipt, and a voided binding no longer counts for 據界. **Dismissing a `CONTRADICTS` binding needs a human authority** (that is what unblocks a reaffirmation). Voiding a `SUPPORTS` binding whose allowance lapsed is done by the system automatically. The record of the contradiction, and of who dismissed it, stays forever.
- **Rejected:** letting any governance actor dismiss a contradiction (software could quietly clear the evidence standing in the way of reaffirming a challenged claim); deleting the binding (loses the contradiction from the hyperedge's history).
- **Prototype note:** `void_binding` currently accepts any governance actor; it would need to require a human for a `CONTRADICTS` binding.

## 6. Allowances with several bounded members (F11): decided 2026-09-19

One allowance per binding, naming the exact **combinations** of meanings the evidence holds under (for example `{the Fund = Alpha, the Trust = North}`). With two ambiguous terms, evidence can hold for one combination and not another, and separate per-term allowances would silently approve the cross product. With one bounded member this is exactly today's rule. When one term is later narrowed, combinations that no longer match are dropped; if none remain the binding is voided (decision 5's mechanism, done by the system).
- **Rejected:** one allowance per member (covers every pairing of its meanings, including ones the evidence never supported); forbidding more than one bounded member (blocks a natural case until someone resolves a term).
- **Prototype note:** the allowance `meanings` becomes a list of member-to-meaning assignments; the single `allowance_receipt_id` slot on the binding stays.

## 7. How far the receipts protect the store (F17): decided 2026-09-19

Three requirements: (a) the evidence receipt records the evidence's **content hash**, so a forged text cannot pass even with a recomputed hash; (b) the invariant **"a record in an admitted-or-later state has its admission receipt, and every admission receipt still has its record"**; (c) a required **integrity check** that a store must offer. In the prototype these caught a forged definition, a deleted claim, a deleted object and a planted admitted row, with no false alarm on an untouched copy.
- **Stated limit:** someone who can rewrite the whole database can rebuild the entire chain, so tamper-evidence against that needs the latest receipt id kept somewhere outside the database. That anchor is not part of this decision.
- **Rejected:** sealing the hash only (deleted or planted rows would still pass); leaving verification to implementations (two stores could disagree on what "intact" means).

---

## Summary: what each decision would change

| # | Decision | Prototype code | Doctrine (when the sync resumes) |
|---|---|---|---|
| 1 | 3 receipt types + `CLEAR`; `PEND`, `BOUND` defined | **applied**: `CLEAR` added; a narrowed term's DSN receipt uses it; the receipt-type vocabulary is now closed by a database CHECK | `Receipt` types and decision values in `ARCHITECTURE.md` §9.1 |
| 2 | meanings and narrowing basis as object fields | already done | `SemanticObject` schema and `AGENTS.md` "Semantic Object Minimum Fields" |
| 3 | id = source + predecessors | already done | the two `id` comments in §9.1 currently say "content"; define it as the source |
| 4 | lost support on an admitted hyperedge = CHALLENGED | already done | correct the walk-through row in `proposed-ambiguity-allowance.md`; state the rule |
| 5 | void, never delete; a human dismisses a contradiction | **applied**: `void_binding` requires a human for `CONTRADICTS`; `voided_receipt_id` added; the system voids automatically when an allowance lapses | binding fields and the rule |
| 6 | one allowance naming combinations | **applied**: an allowance names combinations; `_allowance_state` returns ACTIVE, STANDS or VOID and drops combinations that no longer match; the "one member only" limit is gone | the allowance specification and the `AGENTS.md` subsection |
| 7 | seal hash + invariant + integrity check | already done (`verify_integrity`, hash sealed) | receipt content, the invariant, the required check, the anchor note |

**Prototype:** 87 scenario checks pass and are byte-identical between runs; five sabotages of the new logic (combinations not filtered, the system dismissing a contradiction, voiding without a receipt, a narrowed term recorded as ADMIT, an open receipt vocabulary) are each caught by the matching check. **Doctrine:** all seven applied on 2026-09-20. A cross-check found the doctrine's receipt types, decision values and `SemanticObject` fields identical to the prototype's database schema, and the prototype emits no receipt type the doctrine lacks.
