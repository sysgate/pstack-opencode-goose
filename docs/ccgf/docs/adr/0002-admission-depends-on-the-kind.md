---
status: accepted
---

# Admission depends on the kind of object

A semantic object is admitted by semantic admission (名界) alone. A hyperedge is admitted only after semantic admission, evidence governance, path governance and uncertainty governance have all passed. Evidence, path and uncertainty checks are about a claim, not about a term, so they apply to the hyperedge that makes the claim.

**Considered options**

- *Admission always means all four boundaries, for every object*: rejected. A hyperedge's members are semantic objects, so they would have to wait for the relation they form to be validated before they could be used in it. That is circular.

**Consequences**

- The admission state machine in the architecture note describes hyperedges (claims). A semantic object's lifecycle is its DSN state plus semantic admission; `NARROWED` in that machine is a DSN state, not an admission state.
- "CHI reasons only over admitted semantic objects" means admitted under the object's own rule, not admitted by all four boundaries.
- Neither the architecture note nor `AGENTS.md` says this today, so a reader following the state machine will read "admitted" as all four boundaries for everything.
