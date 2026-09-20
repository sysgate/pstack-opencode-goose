# Findings: what implementing the CCGF doctrine as a store taught us

**PROTOTYPE, THROWAWAY.** Question: when the accepted doctrine is implemented as a SQLite authority store, does it hold together, or do hard cases expose gaps? Run: `python3 scenarios.py` (87 checks, all met; output is byte-identical between runs, so ids and hashes are reproducible).

**Verdict:** the doctrine is implementable and its central rules hold. It also has 19 gaps, found only by building it (16 from the scenarios, 3 more from loading the real CHI glossary, F17 to F19). Seven need a decision before any real build (F1/F2, F3, F5, F6, F9, F11, F17). Two of the gaps are mistakes in drafts I wrote earlier (F6, F15).

## How much to trust the checks

I wrote the scenarios against my own implementation, so passing them first time proves little on its own. To test that the checks can fail, I sabotaged the prototype three ways and confirmed the right checks went red: letting anyone admit (1 check failed), disabling the terminal-state trigger (2 failed), counting tier-4 evidence as sufficient (2 failed). Baseline 0 of 70. What the scenarios do **not** cover is listed at the bottom.

## What held

- The nine-state machine and its legal transitions, including the `UNDER_REVIEW -> ADMITTED` reaffirm edge.
- Admission depends on the kind: a semantic object needs semantic admission alone; a hyperedge needs all four boundaries (ADR 0002).
- "Generation proposes, governance admits": a generative actor cannot admit or decide anything.
- Closed vocabularies and relation signatures reject unknown roles and relation types and wrong role sets; a hyperedge cannot have an unadmitted member.
- Terminal states are never resumed, and the database itself refuses it (a trigger), even against raw SQL.
- Evidence bound, never a member; tier 4 tracked but never sufficient; contradicting evidence on an admitted hyperedge challenges it and withdraws it from projection at once.
- The ambiguity allowance: human only, not the proposer, one binding, meanings named, ambiguity carried in the uncertainty envelope, projected as Bounded Ambiguous, lapses on narrowing.
- Causal loops are caught (徑界 `PATH_BREAK`); a missing uncertainty envelope sends a candidate to review (幅界 `NEEDS_REVISION`).
- Revoking a semantic object cascades to the hyperedges that use it.
- The receipt chain is tamper-evident, and receipts are append-only.

## The gaps (the code tags each as `# FINDING Fn`)

**F1. Receipt types are incomplete.** No type for semantic admission (invented `SEMANTIC_ADMIT`), none for 幅界 (invented `UNCERTAINTY_BOUND`), none for opening a revision (invented `REVISION_OPEN`). *Recommend:* add the three, or state which existing type covers each.

**F2. `Receipt.decision` has no value for "narrowed, cleared for admission".** `ADMIT` was used and reads as if the term were admitted. `PEND` is overloaded (halted, challenged, review opened) and `BOUND` means both bounded ambiguity and an allowance. *Recommend:* add a distinct value for "cleared", and decide whether `PEND` needs splitting.

**F3. `SemanticObject` has nowhere to store candidate meanings or the narrowing basis.** The DSN requirements say to record both, and bounded ambiguity is defined as a known finite set, which must be stored somewhere. The prototype added `meanings` and `narrowing_basis` columns. *Recommend:* add them to the §9.1 schema.

**F4. `UNDER_REVIEW` has two entry points and the state cannot say which.** Whether a review may reaffirm (was admitted) or re-run (never admitted) is not derivable from the state. The prototype reads it from the receipts (has a `HYPEREDGE_ADMIT`). *Recommend:* say that in the doctrine, or record it explicitly.

**F5. "Deterministic id" has no defined inputs.** The prototype hashes the *source* (text, scope, context, predecessors), not the narrowed result. Had the id included label or type, narrowing an admitted bounded term would change its id and break every hyperedge that references it. The lineage rule says "content and predecessors" without defining content. *Recommend:* define content as the source.

**F6. My ambiguity-allowance walk-through was wrong for an admitted hyperedge.** It said that when the term is narrowed to Beta the hyperedge "returns to `PENDING` with `UNSUPPORTED`". That is only true while it is still pending. If it was `ADMITTED`, `ADMITTED -> PENDING` is illegal, and the correct outcome is `CHALLENGED`. (`docs/ccgf/proposed-ambiguity-allowance.md` still shows the wrong row, as history; the applied doctrine text does not repeat it.)

**F7. Reopening a hyperedge: are its evidence bindings carried over?** The doctrine is silent. The prototype does not carry them, so a reopened hyperedge must earn its admission again. *Recommend:* state that.

**F8. `EvidenceRecord` has no lifecycle.** There is no admission state, so tier-4 "tracked, never admitted" has no state to live in (the prototype uses the receipt's `PEND`), and the allowance rule "lapses when the evidence is revised or revoked" cannot be evaluated, because evidence cannot be revised or revoked.

**F9. A dismissed contradiction has no representation.** To reaffirm a challenged hyperedge the contradicting binding must stop counting, and nothing says how that is recorded. The prototype added `void_reason` and a receipt. Without it, a hyperedge challenged by contradicting evidence could never be reaffirmed. *Recommend:* specify how a binding is voided or dismissed.

**F10. The projection labels have no entry for `UNDER_REVIEW`, `DENIED` or `CANDIDATE`.** The prototype maps them to Challenged, Not Projectable and Not Projectable.

**F11. The binding has one `allowance_receipt_id` slot, but a hyperedge can have several bounded members.** One allowance covers one member, so a hyperedge with two bounded members cannot be bound at all. *Recommend:* key allowances by (binding, member), or forbid more than one bounded member.

**F12. Semantic objects have no review resolution.** They share the nine states, but only the hyperedge lifecycle is described. A candidate that a DSN `CONFLICT` sends to `UNDER_REVIEW` has no way out. *Recommend:* describe the object lifecycle, or say objects only ever go `PENDING -> ADMITTED` or `DENIED`.

**F13. The receipt chain is global.** "previous receipt in chain" was read as one sequence for every subject. That totally orders writes and makes any tamper invalidate all later receipts, but serialises every writer. Per-subject chains would allow parallel writes and partial verification but need an anchor. *Recommend:* decide; the prototype worked either way.

**F14. Refused requests leave no trace.** A request that fails closed (for example a generative actor trying to grant an allowance) rolls back and writes nothing. That is safe but unaudited: a probing agent is invisible. The doctrine asks for receipts for admissions, denials and revisions, not for refusals.

**F15. My lineage draft overstated one rationale.** I said a retry after an `UNRESOLVED` term needs a predecessor link to be told from a first attempt. In the prototype an unresolved term stays `PENDING` and is re-narrowed **in place**, so both attempts are already receipts on the same subject. A predecessor link is needed after a *terminal* state (for example a denied term retried), not for unresolved. The lineage design stands; that one justification does not.

**F16. Bounded-ambiguous semantic objects are admitted.** The allowance mechanism needs a hyperedge with a bounded member, and a hyperedge's members must be admitted objects, so the prototype admits bounded ambiguous ones. The doctrine never says so, and the core axiom "reasons only over admitted semantic objects" then covers ambiguous ones. *Recommend:* say it explicitly.

**F17. The receipt chain did not cover evidence or state.** Found by attacking the loaded glossary store: a forged definition with a correctly recomputed content hash, a deleted claim, a deleted semantic object and a planted `ADMITTED` hyperedge all passed the chain check, the hash check and every other check. Only comparing against the source files caught them. Fixed in the prototype by sealing the evidence content hash into the evidence receipt and adding `Store.verify_integrity()` (every evidence text matches its hash and its receipt; every admission receipt still has its record; every admitted-or-later row has its admission receipt). All four attacks are then caught by the store alone, with no false alarm on an untouched copy. *Recommend:* the doctrine should require the evidence `content_hash` in the evidence receipt, and state the invariant "an admitted-or-later record has an admission receipt".

**F18. The closed relation types give a glossary nothing.** A glossary fits only `CLAIM`, so all of the meaning lives in a `PREDICATE` member (four predicate objects: is defined in, belongs to group, is avoided in favour of, must not be confused with). It works, and a qualifying note fits the `CONDITION` role, but `relation_type` then carries no information. Expect pressure to add types such as `DEFINITION`; that is a design choice to make deliberately, not by accident.

**F19. Verification cannot be recorded.** Glossary evidence is `TIER_3_EXTRACTED`, "awaiting verification", and you have reviewed these glossaries. There is no way to record that review or promote the evidence (F8: evidence has no lifecycle), so the store cannot say "verified by a human on this date".

## What loading the real glossary showed about the glossaries themselves

- 73 terms (28 gate, 45 CCGF), 135 avoid entries over 133 distinct aliases (7 with a qualifying note), 45 group memberships, 3 declared collisions.
- **No undeclared collisions:** the only words defined in both contexts are `Scope` and `Reconciliation`, and `CONTEXT-MAP.md` declares both.
- The gate's `Covered tool` says to avoid "scope" while `Scope` is a defined term in the same context. That is intentional (a disambiguation), and the qualifying note now preserves it.
- **A gap in `CONTEXT-MAP.md` (fixed):** it said *Fast path* collides with a CCGF meaning ("the router's fast path serves non-governed work"), but only the gate defines *Fast path*. The doctrine's only mention is one diagram parenthetical, `(Fast-path / Diagnostic only if non-governed)` at `ARCHITECTURE.md` §4, so the map sentence was an inference stated as fact. The map now says only what the sources say, and the CCGF glossary was left alone rather than define a term from that fragment.
- The map's "System One" is TypeSafe's term and is defined in neither glossary, correctly.

## Decisions

The seven findings that blocked a real build (F1/F2, F3, F5, F6, F9, F11, F17) were decided on 2026-09-19; see `DECISIONS.md`. Decisions 1, 5 and 6 are now applied to the prototype (which is why F1, F2, F9 and F11 above describe the state *before* the fix); the rest already matched it. All seven were applied to the doctrine on 2026-09-20.

## What this does not show

Time-overlap checks on paths (§8.4) and hyperpaths over non-causal relations; DSN for hyperedge candidates; authority tiers beyond tier 4; scope namespaces; concurrent writers; a real projection renderer; revision cascades from evidence; performance. Nothing here touches the running gateway or any real data.

## What to do with it

Nothing was applied to any doctrine file. If you resume the doctrine sync, F6 and F15 correct my own drafts and F1/F2, F3, F5, F9 and F11 are the ones a real build cannot avoid deciding.
