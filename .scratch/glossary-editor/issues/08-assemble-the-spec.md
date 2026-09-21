# Assemble the spec

Type: task (AFK, then a user review)
Status: resolved
Blocked by: 

## Question

When every decision on the map is made, write `docs/glossary-editor/SPEC.md`, the hand-off someone can build v2 from, and let the user review it. This is the destination of the map. It indexes every decision, lists the deltas from editor v1, states what is out of scope, and notes the cross-repo dependency (`CHI_GATEWAY_DIR` and the loader's CLI) and the two performance notes. Alongside it, **draft** (do not apply) the doctrine and glossary text: the revise and revoke lifecycle wording, and definitions for **Drift** and **Outside usage** for `docs/ccgf/CONTEXT.md`. Nothing is built and nothing in the doctrine is changed without the user's go-ahead.

The spec must also carry the **closed list of machine reason strings** and the projection-label wording that [What readers say about a withheld term](09-what-readers-say-about-a-withheld-term.md) settled, since the loader writes them and the readers show them.

## Answer

The spec is [docs/glossary-editor/SPEC.md](../../../docs/glossary-editor/SPEC.md): the hand-off from which editor v2 and its loader changes can be built. It indexes every decision (section 13), lists the deltas from editor v1 and from today's loader, states what is out of scope, notes the cross-repo dependency and the two performance notes, carries the closed list of reason strings and the status buckets, and proposes build slices and test cases. Its companion, [proposed-glossary-terms.md](../../../docs/glossary-editor/proposed-glossary-terms.md), holds the **draft** glossary entries (Successor, Predecessor, Outside usage, Drift and Withheld; the user asked for Withheld to be included) and one doctrine paragraph. **Nothing in a glossary or the doctrine was changed.**

Reviewed with the user; the recommendations on the four points below were accepted:
- **A restored claim with unchanged text:** the human is the actor on the bind and the admit of the successor, because there is no new evidence for a human to admit.
- **`--anchor`:** it selects only among removed claims for `revoke`, and only among pending or challenged claims for `verify`; the digest covers claim ids.
- **The hypergraph web view:** out of scope for v2; it stays a snapshot.
- **How v2 is tested:** the v1 practice extended, on scratch stores only, with a sabotage probe per safety rule.

**Rename as one act** stays out of scope for v2. The five glossary drafts stay **proposed**: the user asked for **Withheld** to be included, and nothing is applied without a go-ahead.

