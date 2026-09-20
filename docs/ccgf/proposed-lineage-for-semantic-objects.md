# Proposed: lineage for semantic objects (open gap from L2)

**Status (2026-09-19): APPLIED as drafted, all three recommendations approved (lineage on `SemanticObject`, `predecessor_ids` on `HyperedgeRecord` too, predecessors included in the id). The text below is otherwise kept as written and is now history.**

## The gap

When I applied L2 I worded the reopening rule for hyperedges only ("starts a new `CANDIDATE` that records the earlier hyperedge in its `lineage_hash`"), because `SemanticObject` has no lineage field. The states themselves are shared: semantic objects use the same nine admission states, so a semantic object can also be `DENIED`, `REVOKED` or `CLOSED` and then need replacing.

Concrete case: the term "the Fund" is denied at 名界 for lack of context. The next day better context arrives. Under D3 the term was only ever a semantic candidate, and the doctrine (via the terminal-states rule) says the earlier one is never resumed, so the retry must be a new candidate. Nothing says how the retry is tied to the failed attempt.

## Findings that shape the proposal

1. **Only hyperedges carry lineage.** `HyperedgeRecord.lineage_hash` is "Merkle hash of predecessor hyperedges"; `SemanticObject` has no equivalent (`ARCHITECTURE.md` §9.1; `AGENTS.md` "Semantic Object Minimum Fields").
2. **A hash commits to predecessors but cannot name them.** The rule I applied says the new candidate "records the earlier hyperedge in its `lineage_hash`". A hash can be verified against a known predecessor; it cannot be followed backwards, so "which hyperedge did this one descend from?" has no answer without searching. This applies to the hyperedge rule I already applied, not only to semantic objects.
3. **Ids are "deterministic" with unspecified inputs.** `SemanticObject.id` is "Stable deterministic UUID / hash", `HyperedgeRecord.id` is "Deterministic hyperedge hash ID". If the id is a pure hash of the object's content, a retry with identical content collides with the earlier object's id, and "the earlier one is never resumed" cannot be enforced.
4. **The receipt chain is not a substitute.** `Receipt.previous_receipt_id` is "Hash of preceding receipt in chain (Merkle lineage)", but nothing says whether that is one global chain or one per subject. Leaning on it for object lineage would rest on an ambiguity.
5. **The audit trace from B5 depends on this.** B5 gave `UNRESOLVED` terms a receipt so "a retry can be told from a first attempt". Without a predecessor link, the retry's receipt trail is separate from the first attempt's.
6. **Revocation of a semantic object already cascades.** §8.3 says 修界 cascades invalidations across connected hyperedges. That needs a way to find the hyperedges affected by a replaced object; a predecessor link is what lets a replacement be tied to the object it replaces.

## Proposal

1. **Add lineage to `SemanticObject`, in the same shape as the hyperedge's, plus predecessor ids for both:**
   - `SemanticObject` gains `predecessor_ids: string[]` (ids of the earlier objects this one descends from; empty for a first attempt) and `lineage_hash: string` (a hash over those predecessors and their final receipts).
   - `HyperedgeRecord` gains `predecessor_ids: string[]` alongside its existing `lineage_hash`, so its lineage can be followed, not only verified.
2. **Include the predecessors in the id.** An id is computed from the object's content and its `predecessor_ids`, so a candidate raised after a denial, revocation or closure gets a new id even when its content is identical. Ids stay deterministic: the same inputs always give the same id.
3. **State the terminal-states rule for both kinds.** Remove the "For a hyperedge," qualifier: a reopened, replaced or retried object of either kind is a new `CANDIDATE` naming its predecessors; the earlier one is never resumed.
4. **Leave the receipt chain alone.** Whether `previous_receipt_id` is global or per subject is a separate question, noted below, and object lineage does not depend on it.

## Doctrine edits this would make

| Where | Change |
|---|---|
| `ARCHITECTURE.md` §9.1 `SemanticObject` | Add `predecessor_ids: string[]` and `lineage_hash: string`; id comment says the id is computed from content and predecessors |
| `ARCHITECTURE.md` §9.1 `HyperedgeRecord` | Add `predecessor_ids: string[]`; id comment likewise |
| `ARCHITECTURE.md` §7, terminal-states paragraph | Drop "For a hyperedge,"; say the new candidate names its predecessors |
| `AGENTS.md` "Semantic Object Minimum Fields" (4 copies) | Add `predecessor_ids: list[string]` and `lineage_hash: string` |
| `AGENTS.md` Revision Agent, terminal-states sentence (4 copies) | Same rewording as §7 |
| `docs/ccgf/CONTEXT.md` | Lineage entry: recorded as the ids of the earlier objects plus a hash over them |

Nothing implements the schema, so these are documentation changes only.

## Decisions for you (recommendation first)

1. **Give `SemanticObject` predecessor ids and a lineage hash?** Recommend yes. The alternatives are to state that a semantic object is never replaced or retried (each attempt stands alone, which loses the retry trail B5 depends on and the link the revocation cascade needs), or to rely on the receipt chain (rests on the ambiguity in finding 4).
2. **Also add `predecessor_ids` to `HyperedgeRecord`?** Recommend yes: without it the hyperedge lineage I already applied can be verified but not followed. This widens the change to a schema you did not ask about, so it is your call.
3. **Include predecessors in the id?** Recommend yes: it is what makes "never resumed" enforceable for identical-content retries.

## Left open, not part of this change

- Whether `Receipt.previous_receipt_id` chains all receipts globally or per subject (`ARCHITECTURE.md` §9.1). The docs say "chain" without saying which.
- What id inputs the evidence record uses ("Deterministic content hash ID"). Evidence is not reopened the way objects and hyperedges are, so I have not proposed changing it.
