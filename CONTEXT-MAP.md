# Context Map

## Contexts

- [Permission gate](./CONTEXT.md): reviews an AI coding agent's tool calls before they run and can only add scrutiny
- [CCGF hypergraph](./docs/ccgf/CONTEXT.md): the governed store of admitted knowledge and the vocabulary for admitting, validating and revising it

## Relationships

- **Permission gate ↔ CCGF hypergraph**: independent. The gate is a developer tool, not a CCGF authority, and writes nothing to the hypergraph.
- **Same word, different meaning**: *Scope* is a folder tree in the gate and an operational namespace in CCGF. The gate's *audit log* is not a CCGF *receipt*. "Admission gate" belongs to CCGF and is avoided in the gate context.
- **More same-word collisions**: *Reconciliation* is comparing transcripts with the audit log in the gate and resolving conflicts and revision events in CCGF. *Fast path* is tool calls the gate does not judge; the chain diagram in `docs/ARCHITECTURE.md` §4 also mentions a router "fast-path / diagnostic" route for non-governed work, but the CCGF context does not define it. CHI's *System 1 / System 2* is an authority split between generating and adjudicating, not TypeSafe's "System One" models, which the gate calls for judgments.

## Collisions

PREVIEW of the glossary editor v2 table format (`docs/glossary-editor/SPEC.md` §5). This table is **not yet read by the loader**:
today's `glossary.py` still finds the collisions above by matching their sentences in the prose, and both statements must keep
agreeing until v2's table parser replaces that matching and the prose above is trimmed (the v2 spec's migration order, §8).

| Term | In | Must not be confused with | In | Why |
|---|---|---|---|---|
| Scope | Permission gate | Scope | CCGF hypergraph | a folder tree in the gate, an operational namespace in CCGF |
| Audit log | Permission gate | Receipt | CCGF hypergraph | the gate's audit log is not a CCGF receipt |
| Reconciliation | Permission gate | Reconciliation | CCGF hypergraph | comparing transcripts with the audit log in the gate, resolving conflicts and revision events in CCGF |
| Fast path | Permission gate | fast-path / diagnostic | outside: docs/ARCHITECTURE.md | a router route for non-governed work that CCGF does not define |
| Generative layer (System 1) | CCGF hypergraph | System One | outside: TypeSafe | an authority split between generating and adjudicating, not TypeSafe's models |
| Adjudication layer (System 2) | CCGF hypergraph | System One | outside: TypeSafe | an authority split between generating and adjudicating, not TypeSafe's models |
