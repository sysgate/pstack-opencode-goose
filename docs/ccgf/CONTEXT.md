# CCGF Hypergraph

The governed store of knowledge behind CHI, and the vocabulary CCGF uses to admit, bind, validate and revise it. Model output is only ever a candidate here; governance admits.

## Language

### The hypergraph

**Hypergraph**:
The store of admitted knowledge, in which one relation can join any number of semantic objects at once. Binary pairs lose the context that makes a relation checkable, so the hypergraph does not decompose relations into pairs.
_Avoid_: knowledge graph, binary graph

**Semantic object**:
A typed thing the hypergraph reasons about: a semantic candidate that has been narrowed and admitted.
_Avoid_: node, vertex, entity

**Hyperedge**:
An admitted relation joining any number of semantic objects, each in an explicit role, valid for a stated time and scope. It stays a hyperedge when later revised or revoked.
_Avoid_: edge, link, relationship

**Hyperedge candidate**:
A proposed relation that has not been admitted. Never treated as knowledge.
_Avoid_: draft hyperedge, pending hyperedge

**Admission**:
CCGF's acceptance of a candidate as governed knowledge, leaving a receipt. What it requires depends on the kind: a semantic object needs semantic admission alone, a hyperedge needs semantic admission, evidence governance, path governance and uncertainty governance.
_Avoid_: approval, commit, acceptance

**Role**:
The part a semantic object plays in one hyperedge, such as subject or condition, drawn from a closed list of seven. The same object can hold different roles in different hyperedges.
_Avoid_: type (that belongs to the object)

**Relation type**:
The kind of relation a hyperedge asserts: claim, obligation, risk control, or causal. A closed list, extended only by amending the doctrine.
_Avoid_: edge type

**Relation signature**:
The roles a relation type requires and allows. Semantic admission rejects a hyperedge whose members do not satisfy its type's signature.
_Avoid_: schema, template

**Revision event**:
A ledger record of a state change to a governed object. Not a relation between semantic objects.
_Avoid_: amendment

**Scope**:
The operational namespace within which a semantic object or hyperedge holds.
_Avoid_: tenant, domain

**Validity interval**:
The time window during which a hyperedge is active.
_Avoid_: timestamp, expiry

**Evidence binding**:
The attachment of evidence to a hyperedge as supporting or contradicting it. Evidence is bound to a hyperedge, never a member of it.
_Avoid_: citation, evidence edge

**Uncertainty envelope**:
The bounded statement of how far a hyperedge can be trusted, applied to the whole relation rather than to one member.
_Avoid_: confidence score

**Receipt**:
The sealed, chained record that one decision was made about a governed object. A hyperedge is admitted under a receipt.
_Avoid_: audit record, log entry

**Governance envelope**:
Everything that travels with a hyperedge to make it governed: admission state, authority tier, receipt, lineage and uncertainty envelope.
_Avoid_: metadata

**Lineage**:
The chain of earlier hyperedges or semantic objects an item descends from, whether by revision, by reopening, or as a candidate raised after a denial, recorded as the ids of its predecessors and a hash over them. An earlier one is never resumed.
_Avoid_: history

**Hyperpath**:
An ordered run of hyperedges along which an inference or causal claim travels. Valid only if neighbours connect through compatible roles, their validity intervals overlap, no premise is unsupported, and causal paths never loop.
_Avoid_: chain (the CCGF chain is the sequence of governance stages), traversal

### Narrowing and admission

**Semantic candidate**:
A term still being narrowed, kept as a structured record with its original text and the meanings considered, never as a bare string. Not yet admitted.
_Avoid_: raw term, mention

**Semantic admission**:
The first of the five boundaries (名界): decides whether a narrowed candidate becomes a semantic object. Contains DSN and the admission gate, and comes before evidence.
_Avoid_: term validation

**Deterministic semantics narrowing (DSN)**:
The mechanism inside semantic admission that turns an ambiguous or under-specified candidate into a typed, scoped meaning on a recorded basis. A model's most probable reading alone never counts, even when a model performs the steps. Not a sixth boundary.
_Avoid_: disambiguation, entity resolution

**Narrowing basis**:
The recorded reason a candidate was narrowed to a meaning (context, ontology, evidence, policy, source, or an explicit user constraint), with the alternatives considered.
_Avoid_: rationale, justification

**Semantic type**:
The domain type committed to a candidate before admission.
_Avoid_: class, category

**DSN state**:
The outcome of narrowing one candidate: narrowed, bounded ambiguous, unresolved, conflict, or denied. Evidence binds only to a narrowed candidate, except under an ambiguity allowance for bounded ambiguity.
_Avoid_: narrowing status

**Bounded ambiguity**:
A DSN state in which a known, explicit, finite set of meanings remains. Not the same as unresolved, where no such set could be established; insufficient context alone decides neither.
_Avoid_: partial narrowing, uncertainty (that belongs to the uncertainty envelope)

**Voided binding**:
An evidence binding withdrawn from counting, kept with its reason and the receipt that recorded it, never deleted.
_Avoid_: deleted binding, removed evidence

**Ambiguity allowance**:
A human authority's recorded permission for one evidence binding on a hyperedge that has a bounded-ambiguous member, naming the exact combinations of meanings the evidence holds under. Covers that binding only; combinations that no longer match are dropped as terms are narrowed, and the binding is voided if none remains.
_Avoid_: waiver, override, exception

### Boundaries and the chain

**Candidate**:
Anything generated that has not been admitted: a semantic candidate, a hyperedge candidate, or a piece of candidate evidence. Generation proposes; only governance admits.
_Avoid_: draft, suggestion

**Generative layer (System 1)**:
Whatever proposes candidates, whether a cloud or a local model. Its output is candidate state regardless of the model's capability.
_Avoid_: fast thinking, model tier

**Adjudication layer (System 2)**:
The deterministic validators and the authority store that enforce the boundaries and issue receipts.
_Avoid_: slow thinking, reasoning model

**Boundary**:
One of exactly five governance checks, applied in order: semantic admission (名界), evidence governance (據界), path governance (徑界), uncertainty governance (幅界), revision governance (修界). Semantic agreement takes precedence over evidence.
_Avoid_: layer, pillar

**Evidence governance (據界)**:
The boundary that binds claims to provenance, authority and receipts. On failure the claim is not trusted or projected.
_Avoid_: fact checking

**Path governance (徑界)**:
The boundary that validates inference, causal and dependency chains as valid hyperpaths. On failure the claim is sent back to semantic admission.
_Avoid_: reasoning check

**Uncertainty governance (幅界)**:
The boundary that bounds confidence, scope, applicability and ambiguity. On failure revision handling is triggered.
_Avoid_: confidence scoring

**Revision governance (修界)**:
The boundary that reconciles contradiction, state change, revocation and closure. On failure the claim does not continue as stable knowledge.
_Avoid_: versioning, editing

**Governance chain**:
The required sequence every governed transaction follows: router, DSN, semantic admission, evidence binding, path validation, uncertainty bounding, projection, reconciliation, closure. Stages and boundaries are not one-to-one: the router and projection belong to no boundary, and DSN sits inside semantic admission. G-A-T-P-R-C is shorthand only: generation (before the chain), admission (router through uncertainty bounding), trace (every stage), projection, reconciliation, closure.
_Avoid_: pipeline

**Cognitive Router**:
The first stage of the chain. Classifies the kind of cognitive work (deterministic reasoning, evidence extraction, semantic admission, or hybrid) and sends it down the governed path. Routes only; never admits.
_Avoid_: dispatcher

**Projection**:
A rendering of admitted, unchallenged knowledge into a UI, wiki, report or agent-visible summary. Derived and rebuildable, withdrawn when the claim is challenged or revoked, and never authority.
_Avoid_: publishing, output

**Reconciliation**:
Resolving conflicts, stale claims, ambiguity and revision events after admission.
_Avoid_: sync

**Closure**:
Marking a decision, state, artifact or reasoning path as closed, with a receipt.
_Avoid_: completion

**Trace**:
The recording of provenance, hashes, receipts, paths and lineage at every stage of the chain. Not a stage of its own.
_Avoid_: logging

**Fail closed**:
When a boundary cannot establish what it checks, the result is the more restrictive state (pending, denied, unknown, conflict), never admission.
_Avoid_: safe default

**Non-governed prototype**:
A shortcut past a chain stage, allowed only when explicitly marked, isolated by a test, and tracked by a follow-up to replace it with the governed path.
_Avoid_: bypass, temporary hack

**Verification**:
A human authority's decision that extracted (tier 3) evidence may be admitted, recorded on the admission receipt with who verified it and any note.
_Avoid_: approval, sign-off

**Authority tier**:
The rank of an evidence source: canonical provenance, admitted hypergraph state, extracted candidate evidence, generative hypotheses. Generative hypotheses are tracked as candidates but never admitted, and so never bound to a hyperedge.
_Avoid_: trust level, source score

**Admission state**:
Where a semantic object or hyperedge stands in its lifecycle: candidate, pending, admitted, denied, challenged, under review, revised, revoked, or closed. Not a DSN state and not a projection label.
_Avoid_: status, lifecycle stage

**Failure reason**:
Why a boundary stopped a candidate: the DSN state (semantic admission), unsupported or untrusted (evidence), path break (path), needs revision (uncertainty). Recorded on the receipt, never stored as an admission state.
_Avoid_: error, rejection code

**Projection label**:
How a piece of knowledge is worded when shown: admitted, pending evidence, bounded ambiguous, challenged, revised, revoked, closed, unknown, or not projectable. Derived from stored state, never stored as authority.
_Avoid_: status badge
