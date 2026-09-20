# Proposed relation types and roles (items B6 and B7)

**Status (2026-09-19): APPLIED as drafted, all five recommendations approved, including the relation-signature table as written (the user was asked to review it, since it has no source in the doctrine). The text below is otherwise kept as written and is now history.**

One deviation from the edit table: the `AGENTS.md` list item "Causal paths" was renamed "Causal relationships" (matching "Risk relationships"), so the list does not keep the word that decision 2 removed from the schema. The list is now Claims, Obligations, Risk relationships, Control mappings, Causal relationships.

Relation types and roles are both closed vocabularies that a hyperedge's schema depends on, and each is listed inconsistently. They are drafted together because the missing link between them, the relation signature, is defined by neither document.

## Current lists

**Relation types**

| Where | Values |
|---|---|
| `AGENTS.md:587-596` "Hyperedges may represent" | Claims, Obligations, Risk relationships, Parties, Timelines, Control mappings, Causal paths, Inquiry relationships, Revision events, Projection eligibility (10) |
| `ARCHITECTURE.md:314` `relation_type` | CLAIM, OBLIGATION, RISK_CONTROL, CAUSAL_PATH, REVISION_EVENT (5) |
| `ARCHITECTURE.md:238` diagram | CONTRACTUAL_OBLIGATION |

**Roles**

| Where | Values |
|---|---|
| `ARCHITECTURE.md:261` §8.2 (open, "e.g.") | SUBJECT, OBJECT, PREDICATE, CONDITION, SCOPE_QUALIFIER, BENEFICIARY, ASSUMPTION (7) |
| `ARCHITECTURE.md:330` `HyperedgeMember.role` (closed enum) | SUBJECT, PREDICATE, OBJECT, CONDITION, QUALIFIER (5) |
| `ARCHITECTURE.md:239-243` diagram | Debtor, Beneficiary, Condition, Target |

## Findings that shape the proposal

1. **Four of the ten "may represent" items are not hyperedge kinds.**
   - *Parties* are semantic objects that take roles, not a relation.
   - *Timelines*: every hyperedge already has a validity interval (`valid_from`, `valid_to`).
   - *Inquiry relationships* are defined nowhere in either document.
   - *Projection eligibility* is something CHI decides (`AGENTS.md:800`), and projection is a derived, rebuildable view (D8). Storing it as a hyperedge would make a derived label into authority.
2. **"Revision event" has two meanings.** CHI's own ledger records of state changes (`ARCHITECTURE.md:387`, `AGENTS.md:164`, `AGENTS.md:573`), and a hyperedge relation type. As a relation type its members would have to be the governed objects that were revised, but a hyperedge's members are semantic objects (ADR 0002 and the glossary). CHI's own revisions are already captured by lineage, the `REVISION_CLOSE` receipt and the admission state.
3. **`CAUSAL_PATH` clashes with "hyperpath".** A hyperpath is a run of hyperedges. A hyperedge of this relation type is one causal link in such a run, so calling the type a "path" muddles the two.
4. **Relation signatures are promised but never defined.** `ARCHITECTURE.md:268` says 名界 "validates relation signatures", yet no document says which roles a relation type requires.
5. **The diagram already maps onto the 7-role list.** Debtor is SUBJECT, Beneficiary is BENEFICIARY, Condition is CONDITION, Target is OBJECT. Only Debtor and Target are labels rather than roles.

## Proposal

### Relation types: a closed list of four, extensible by amendment
`CLAIM`, `OBLIGATION`, `RISK_CONTROL`, `CAUSAL`.

| `AGENTS.md` item | Becomes |
|---|---|
| Claims | `CLAIM` |
| Obligations | `OBLIGATION` (the diagram's `CONTRACTUAL_OBLIGATION` becomes `OBLIGATION`) |
| Risk relationships, Control mappings | `RISK_CONTROL` |
| Causal paths | `CAUSAL` (renamed from `CAUSAL_PATH`) |
| Revision events | Removed as a relation type; see decision 3 |
| Parties, Timelines, Inquiry relationships, Projection eligibility | Removed from the list; not hyperedge kinds |

An unknown relation type is rejected (fail closed). Adding one is a doctrine amendment that states its meaning and its signature.

### Roles: a closed list of seven
`SUBJECT`, `OBJECT`, `PREDICATE`, `CONDITION`, `SCOPE_QUALIFIER`, `BENEFICIARY`, `ASSUMPTION`.
- The `HyperedgeMember.role` enum becomes this list; `QUALIFIER` is dropped in favor of `SCOPE_QUALIFIER`; §8.2 stops saying "e.g." and says the list is closed.
- Debtor and Target in the diagram are shown as relation-type-specific display labels for `SUBJECT` and `OBJECT`.
- An unknown role is rejected.

### Relation signature: each relation type states which roles it requires and allows
名界 rejects a hyperedge whose members do not satisfy its type's signature. **The table below is new design, not taken from either document; please review it rather than approve it by default.**

| Relation type | Required roles | Allowed roles |
|---|---|---|
| `CLAIM` | `SUBJECT` | `PREDICATE`, `OBJECT`, `CONDITION`, `ASSUMPTION`, `SCOPE_QUALIFIER` |
| `OBLIGATION` | `SUBJECT` (obligor), `OBJECT` (what is owed), `BENEFICIARY` | `CONDITION`, `ASSUMPTION`, `SCOPE_QUALIFIER` |
| `RISK_CONTROL` | `SUBJECT` (risk or asset at risk), `OBJECT` (control) | `CONDITION`, `ASSUMPTION`, `SCOPE_QUALIFIER` |
| `CAUSAL` | `SUBJECT` (cause), `OBJECT` (effect) | `CONDITION`, `ASSUMPTION`, `SCOPE_QUALIFIER` |

`BENEFICIARY` is allowed only in `OBLIGATION`. `PREDICATE` is allowed only in `CLAIM`, where a named predicate object is needed; elsewhere the relation type is the predicate.

Two overlaps I am keeping and flagging: `SCOPE_QUALIFIER` as a member overlaps the hyperedge's own `scope` field, and `PREDICATE` as a member overlaps `relation_type`. Both are in the source documents, so removing them is a separate decision.

## Doctrine edits this would make

| Where | Change |
|---|---|
| `AGENTS.md:587-596` (all 4 copies) | "Hyperedges may represent" reduced to Claims, Obligations, Risk relationships, Control mappings, Causal paths |
| `ARCHITECTURE.md:238` diagram | `Type: OBLIGATION` |
| `ARCHITECTURE.md:261` §8.2 | Role list stated as closed; note on Debtor and Target labels |
| `ARCHITECTURE.md:314` and `:330` | `relation_type: CLAIM \| OBLIGATION \| RISK_CONTROL \| CAUSAL`; `role:` the seven roles |
| `ARCHITECTURE.md` §8 | New short subsection "Relation signatures" with the table |
| `docs/ccgf/CONTEXT.md` | New terms Relation signature and Revision event; Relation type and Role entries updated |

## Decisions for you (recommendation first)

1. **Drop Parties, Timelines, Inquiry relationships and Projection eligibility from the hyperedge list?** Recommend yes: none is a relation among semantic objects, and one would store a derived label as authority.
2. **Rename `CAUSAL_PATH` to `CAUSAL`?** Recommend yes. Nothing implements the schema, so it costs one word in the docs and removes a clash with "hyperpath".
3. **Remove `REVISION_EVENT` as a relation type, and define "revision event" as a ledger record of a state change to a governed object?** Recommend yes: that is what the three other mentions already mean, and it avoids members that are not semantic objects. The alternative is to keep it and define it as a real-world change among semantic objects, such as a document being superseded, which the docs never say.
4. **Adopt relation signatures with the table above?** Recommend adopt, after you review the table. It is the only part of this draft with no source in the doctrine.
5. **Roles: the closed list of seven, with Debtor and Target as display labels?** Recommend yes.

## Not covered

Whether `SCOPE_QUALIFIER` and `PREDICATE` should exist as roles at all (see the overlaps above). The white paper's hyperedge example (C1) is a separate `.docx` step.
