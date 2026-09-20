# Proposed: an evidence lifecycle (decision D4; closes F8 and F19)

**Status (2026-09-20): APPLIED to the doctrine (`ARCHITECTURE.md` §9.1 and §9.2, the four `AGENTS.md` copies, the glossary), with decisions E1 to E3 as recorded at the end. The code (slice 3) is built and verified on the branch hypergraph-store (uncommitted); the text below is otherwise kept as drafted.**

## Why

The doctrine's `EvidenceRecord` has no lifecycle: no admission state, no way to revoke, and no way to record that a human verified extracted evidence. That left two findings open (F8: "the allowance rule 'lapses when the evidence is revised or revoked' cannot be evaluated"; F19: "a human review of extracted evidence cannot be recorded"). Meanwhile the gateway already keeps a `candidate_evidence` table with an `evidence_state` and an `admission_receipt_id` that nothing has ever used.

## Facts (read on 2026-09-20, from the verified backup, read-only)

| Fact | Detail |
|---|---|
| Candidates in the ledger | 1,071, **all `CANDIDATE`, none admitted** (`admission_receipt_id` never set) |
| Kinds | 1,066 `model_response` (1,058 from goose, 8 from opencode), 5 `tool_output` (goose) |
| Verifiable | For **every** row, `evidence_hash` = SHA-256 of the canonical JSON of the stored body. No body is missing |
| Provenance | Every row points at an existing request receipt (0 orphans) |
| How the gateway writes it | **Insert-only.** The only code that touches `candidate_evidence` is `insert_candidate_evidence`; nothing ever updates or deletes a row |
| Doctrine today | `ARCHITECTURE.md` §9.1 `EvidenceRecord`; §9.2 tiers ("Tier 4 records are tracked as candidates; they are never admitted evidence and never satisfy 據界 alone"); adapter doctrine ("adapters must output candidate types, never admitted types"); `AGENTS.md` Evidence Agent ("Model-generated text is never evidence by itself") |

## The proposal

1. **Evidence has a lifecycle:** `CANDIDATE`, then `ADMITTED` or `DENIED`; `ADMITTED` may become `REVOKED`. `DENIED` and `REVOKED` are terminal: a retry is a new candidate, as for objects and hyperedges.
2. **Two records, one lifecycle.** A *candidate* is raw material with provenance (source agent, kind, body, content hash, the request it came from). *Admitted evidence* is a content-addressed record created **only** by admission, which points back at its candidate. The gateway's `candidate_evidence.evidence_state` and `admission_receipt_id` become the candidate's lifecycle.
3. **Authority tier is decided by a rule, not a per-source table:** output of the generative layer is tier 4; deterministic extraction is tier 3; tier 1 needs a verifiable canonical artifact; tier 2 derives from admitted hypergraph state, never from a candidate row. For the gateway that means `model_response` is tier 4 and `tool_output` is tier 3.
4. **Tier 4 is never admitted.** A tier-4 candidate stays a candidate (it may be denied). See decision E1 for what that means for binding.
5. **Admitting tier 3 is verification.** In v1 only a human authority may verify. The admission receipt records who and any note, which is what F19 asked for.
6. **Admission checks the hash.** The SHA-256 of the canonical JSON of the body must equal the candidate's stored hash. A candidate with no body, or a body that no longer matches, cannot be admitted. The hash is sealed in the admission receipt (decision 7).
7. **Revoking admitted evidence voids every binding that uses it**, done automatically by the system with `REVISION_CLOSE` receipts (decision 5's mechanism). A hyperedge left without support becomes `CHALLENGED` if it was `ADMITTED` and stays `PENDING` with `UNSUPPORTED` recorded otherwise (decision 4's rule). This makes the allowance lapse rule "evidence revised or revoked" evaluable.
8. **No new receipt vocabulary is needed.** Admission and denial are `EVIDENCE_ADMIT` with `ADMIT` or `DENY`; revocation is `REVISION_CLOSE` with `REVOKE`.

## What existing data does

The 1,066 model responses can never be admitted (rule 4). The 5 tool outputs are eligible for verification. **No existing row is changed by adopting this;** only a later, explicit verification would touch one.

## Doctrine edits this would make (if approved)

| Where | Change |
|---|---|
| `ARCHITECTURE.md` §9.1 `EvidenceRecord` | Add `candidate_id`; state that a record exists only through admission |
| `ARCHITECTURE.md` §9.2 | New paragraph: the lifecycle, the tier rule, tier 4 never admitted, tier 3 admitted only by verification, revocation cascade |
| `AGENTS.md` Evidence Agent | The same rules as short bullets; two required tests (tier 4 cannot be admitted; a hash mismatch cannot be admitted) |
| `AGENTS.md` and `ARCHITECTURE.md` allowance text | "or when the evidence is revised or revoked" now points at revocation |
| Glossary | Update **Authority tier**; new term **Verification** |
| Prototype scenario 4 | Changes under E1 option A: a tier-4 record could no longer be bound at all |

## Decisions for you (recommendation first)

**E1. Can a tier-4 candidate be bound to a hyperedge?** Recommend **no**: it is never admitted, so it never appears as support, and nothing generative can even sit next to real evidence. That is stronger than the current wording ("never satisfies 據界 *alone*"), which would then need a small tightening. *Alternative:* allow the binding, recorded but never counted, which keeps tier 4 visible on a hyperedge as a hypothesis but requires bindings to point at unadmitted candidates.

**E2. How is the gateway's table guarded?** The state must move on `candidate_evidence`, but migrations may not alter gateway tables, and the gateway itself only ever inserts. Recommend **refusal-only triggers on `candidate_evidence`**: they can only abort an illegal update (a state move outside the lifecycle, or any change to the body, hash, kind or request link) and never write anything, so the gateway cannot be affected. This needs one narrow exception to the "additive only" rule, enforced by the migration guard (a trigger on a gateway table must contain nothing but `RAISE`). *Alternatives:* Python and the integrity check only (no database enforcement on that table), or a separate lifecycle table that leaves the gateway table untouched forever (its `evidence_state` would then stay `CANDIDATE` and mislead).

**E3. Who may verify tier-3 evidence?** Recommend a **human authority only** in v1, consistent with allowances and contradiction dismissal. *Alternative:* a human, or the system running a registered deterministic verifier. That would need the verifier itself specified first, and none exists.

## Decisions made (2026-09-20)

All three recommended options were chosen.
- **E1:** a tier-4 candidate can never be bound to a hyperedge. Tier 4 is never admitted, so it never appears as support. The sentence "never satisfy 據界 alone" in `ARCHITECTURE.md` §9.2 and the glossary gets tightened when this is applied.
- **E2:** refusal-only triggers on `candidate_evidence`. This is **one narrow exception to the additive-only rule**, to be enforced by the migration guard: a trigger on a gateway table is allowed only if its body contains nothing but `RAISE`, so it can abort an illegal update and can never write. The gateway only inserts into this table, so it cannot be affected.
- **E3:** only a human authority may verify tier-3 evidence.

**What applying it involved**
- The doctrine edits listed above, to `ARCHITECTURE.md`, the four `AGENTS.md` copies and the glossary: DONE on 2026-09-20 at your go-ahead.
- Code (slice 3): a migration for `evidence_records`, refusal-only triggers on `candidate_evidence` behind a stricter migration guard, the promotion and revocation operations, and tests including a sabotage probe for each rule.
- Prototype scenario 4 changes (a tier-4 record can no longer be bound); the prototype is throwaway and is left as it is unless you want it updated.

