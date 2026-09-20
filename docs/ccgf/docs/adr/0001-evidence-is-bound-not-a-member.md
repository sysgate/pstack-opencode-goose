---
status: accepted
---

# Evidence is bound to a hyperedge, not a member of it

A hyperedge's members are semantic objects, each in a role. Evidence attaches from outside through an evidence binding that says whether it supports or contradicts the relation. Making evidence a member would mean a hyperedge could only ever list what backs it, and could not carry what disputes it.

**Considered options**

- *Evidence as a member*: rejected. It is the shape the white paper's hyperedge example uses (`evidence_set`, `source_authority`, `policy_scope`, `inference_path` alongside the claim). It has no place for contradicting evidence, and it lets evidence take a role like a semantic object without going through narrowing.

**Consequences**

- The architecture note's `HyperedgeMember` / `HyperedgeEvidenceBinding` split stays as written. The white paper's example is loose wording, not a competing design; the white paper itself has not been edited.
- "Evidence support" is not a relation type: a hyperedge gains support through bindings, not by being an evidence-support relation. The list of things hyperedges "may represent" in `AGENTS.md` still includes it and needs reconciling.
- Switching later would change the stored shape of every admitted hyperedge and its receipts.
