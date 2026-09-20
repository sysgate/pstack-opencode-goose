# Context Map

## Contexts

- [Permission gate](./CONTEXT.md): reviews an AI coding agent's tool calls before they run and can only add scrutiny
- [CCGF hypergraph](./docs/ccgf/CONTEXT.md): the governed store of admitted knowledge and the vocabulary for admitting, validating and revising it

## Relationships

- **Permission gate ↔ CCGF hypergraph**: independent. The gate is a developer tool, not a CCGF authority, and writes nothing to the hypergraph.
- **Same word, different meaning**: *Scope* is a folder tree in the gate and an operational namespace in CCGF. The gate's *audit log* is not a CCGF *receipt*. "Admission gate" belongs to CCGF and is avoided in the gate context.
- **More same-word collisions**: *Reconciliation* is comparing transcripts with the audit log in the gate and resolving conflicts and revision events in CCGF. *Fast path* is tool calls the gate does not judge; the chain diagram in `docs/ARCHITECTURE.md` §4 also mentions a router "fast-path / diagnostic" route for non-governed work, but the CCGF context does not define it. CHI's *System 1 / System 2* is an authority split between generating and adjudicating, not TypeSafe's "System One" models, which the gate calls for judgments.
