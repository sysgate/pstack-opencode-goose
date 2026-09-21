# Proposed glossary and doctrine text for the glossary editor v2

Status: **PROPOSED, NOT APPLIED.** Nothing in `docs/ccgf/CONTEXT.md`, `AGENTS.md`, `docs/ARCHITECTURE.md` or `CONTEXT-MAP.md` has been changed. Each block below is text for the user to accept, edit or reject; it is applied only with the user's go-ahead, and then through the glossary editor and the doctrine sync, not by hand. It belongs to [the v2 specification](SPEC.md). The user asked (2026-09-20) for **Withheld** to be included with the other four; the set as a whole is still proposed.

## 1. Glossary terms for `docs/ccgf/CONTEXT.md`

Format matches the file: `**Term**:`, one paragraph, then `_Avoid_:`. The proposed group is noted above each.

**Group "The hypergraph"** (beside **Lineage**):

```
**Successor**:
The claim that replaces an earlier one by naming it as its predecessor, raised after that claim was revised, revoked or denied. It starts pending and must earn its admission again; the earlier one is never resumed.
_Avoid_: new version, replacement

**Predecessor**:
An earlier hyperedge or semantic object that a later one names in its lineage. It is terminal, and is never resumed.
_Avoid_: old version, previous version

**Outside usage**:
A phrase quoted from somewhere no glossary defines, such as a diagram label or another product's term, recorded only so that a defined term can be kept apart from it. It is never a term and asserts nothing about its own meaning.
_Avoid_: external term, foreign term
```

**Group "Boundaries and the chain"** (beside **Reconciliation**):

```
**Drift**:
A change to a glossary source that has been saved but not yet loaded, so the store still asserts the earlier text. It ends when load withholds the claim. It is a relation between a source and the store, not an admission state.
_Avoid_: stale, out of sync
```

**Group "Boundaries and the chain"**, included at the user's request (the loader's messages use the word and no glossary defines it):

```
**Withheld**:
Not asserted: a claim that is not admitted, or that is admitted but fails the integrity check. A projection never shows a withheld claim as knowledge, and the reader says why.
_Avoid_: hidden, suppressed
```

Notes:
- These five are the words the v2 specification uses that no glossary defines. Each was checked against both glossaries for a clash; "successor" and "predecessor" complete the lineage vocabulary (the glossary already says "the ids of its predecessors").
- "Drift" is deliberately narrow: an edit saved but not yet loaded. A claim that load has already withheld is *challenged*, an existing admission state.
- Applying these adds entries to `docs/ccgf/CONTEXT.md`; the new claims are then loaded and verified through the editor like any other new term.

## 2. Doctrine text for `docs/ARCHITECTURE.md` section 9.2 (and the matching `AGENTS.md` bullets)

Proposed addition, after the evidence lifecycle block:

> **Revising and retiring glossary claims.** When the source text of a loaded claim changes, or the statement disappears, the machine may only make the store *less* assertive: a deterministic actor (`sys:`) challenges the admitted claim, which withholds it at once and reversibly. Only a human authority makes it more assertive again (verifying the new text, or reaffirming the claim when the text returns) or final (revoking it, or denying a claim that was never verified). A revised claim is a new claim that names the earlier one as its predecessor; the earlier one is never resumed and its evidence stays admitted as a record of what the source said. A revoked or denied claim whose statement returns is reopened the same way, as a successor that a human verifies.

Rationale and honesty about the gap:
- The doctrine already says a reopened claim "starts a new `CANDIDATE` that names the earlier one in its `predecessor_ids`; the earlier one is never resumed" and lists the states. What it does not say is **which actor kinds may make which move**; that split is stated only in `hypergraph/actors.py` and its tests, and the database checks no actor kind on claim moves (only verifying tier-3 evidence, granting an ambiguity allowance and voiding a contradicting binding are human-only in the database).
- The paragraph above therefore states a **policy the loader and editor enforce**, not a rule the store enforces. If the user wants it enforced in the store as well (for example with refusal-only triggers, as was done for candidate evidence), that is a separate piece of work outside the v2 specification.
- It changes no state, no receipt type and no legal transition.
