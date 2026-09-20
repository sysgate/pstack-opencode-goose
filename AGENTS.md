# AGENTS.md — Personal CHI Platform / CCGF

## Agent Compatibility and Scope

This is the canonical project instruction file for agents working on the **personal CHI Platform** and its **CHI Cognitive Governance Framework (CCGF)**.

It applies to this directory and every descendant directory unless a more specific `AGENTS.md` in a descendant directory adds or overrides instructions for that subtree.

- **Codex:** discovers this file automatically when started in this project.
- **Goose:** `.goosehints` may bootstrap this file. Read this file completely before acting; `.goosehints` is not a second source of policy.
- **Claude Code / OpenCode / other agents:** may use this file when explicitly supplied as project instructions.

Platform safety policies and the user's current request take precedence over this file.

When instructions at the same level conflict, stop and surface the conflict instead of silently choosing one.

In this document:

- **must**, **must not**, and **required** are binding.
- **should** is the default unless the task supplies a documented reason to depart.

---

## Canonical Name

Use the name:

```text
CHI
CHI Platform
personal CHI Platform
CHI Cognitive Governance Framework
CCGF
```

Do **not** rename the system to another project name.

Do **not** refer to CHI as “Aegis.”

---

## Purpose

This repository implements the **personal CHI Platform**: a contract-governed, assurance-native hypergraph intelligence system.

CCGF is the governance control plane for CHI. It transforms generative cognition into admitted, evidenced, traceable, bounded, revisable, and renderable knowledge.

CHI is not a generic chatbot workspace, ordinary RAG stack, unconstrained agent workflow, or prompt pattern. It is a governed reasoning platform where generative models may propose, but only CHI authorities may admit, trace, project, reconcile, or close knowledge.

The central rule is:

> **Generation proposes. Governance admits.**

The core doctrine is:

> **No Accord. No Coherence. No Render.**  
> **Accord before Knowledge; Knowledge before Display.**

Agents working in this repository must preserve CHI’s authority model, deterministic evidence handling, and fail-closed behavior.

---

## Operating Protocol

For every task in scope:

1. Read the relevant code, schemas, tests, and nearer instruction files before editing.
2. Classify the work through the Cognitive Router.
3. Record the classification in an artifact only when the task creates or changes a governed cognition flow; do not manufacture receipts for ordinary repository maintenance.
4. Treat model output, extracted text, summaries, and proposed code as candidates until the applicable governance gates admit them.
5. Make the smallest coherent change that satisfies the request and preserves the CHI/CCGF invariants.
6. Validate in proportion to risk. Run focused tests first, then broader checks when justified.
7. Never claim a command, test, citation, receipt, or governance gate succeeded unless it was actually checked.
8. Report what changed, what was validated, and any unresolved ambiguity, missing evidence, or residual risk.

Do not assume a particular agent, model, editor, shell, or tool name. If a named tool is unavailable, use an equivalent safe mechanism and preserve the same governance outcome.

Do not expose secrets or copy credentials into prompts, logs, receipts, fixtures, or source files.

---

## Canonical Doctrine

### CCGF Governance Law

Use the following law as the controlling doctrine for all CHI/CCGF work:

```text
未定其義，不可正其名；
未正其名，不可論；
未立其據，不可信；
未明其徑，不可推；
未守其幅，不可判；
未修其變，不可續。
```

English operational translation:

```text
If meaning is not narrowed, the name cannot be admitted.
If the name is not admitted, it cannot be discussed as knowledge.
If evidence is not established, it cannot be trusted.
If the path is not traceable, it cannot be inferred.
If the uncertainty envelope is not bounded, it cannot be judged.
If revision is not handled, it cannot continue.
```

### Core Axiom

```text
CHI never reasons over words.
CHI reasons only over admitted semantic objects.
```

Agents must enforce this axiom in code, schemas, tests, documentation, UI projections, and generated artifacts.

---

## Required CCGF Chain

All governed cognition must follow this canonical chain:

```text
Input
  -> Cognitive Router
  -> Deterministic Semantics Narrowing (DSN)
  -> Semantic Admission
  -> Evidence Binding
  -> Path Validation
  -> Uncertainty Bounding
  -> Projection
  -> Reconciliation
  -> Closure
```

Do not bypass this chain for convenience.

If an implementation temporarily shortcuts a stage for prototyping, mark it explicitly as:

```text
NON_GOVERNED_PROTOTYPE
```

Add a test showing the shortcut is isolated, and create a follow-up issue to replace it with the governed path.

---

## CHI Execution Mnemonic

The CHI Chain may also be summarized as:

```text
G -> A -> T -> P -> R -> C
```

Where:

| Stage | Name | Meaning |
|---|---|---|
| G | Generation | Produce candidates, drafts, hypotheses, extracted facts, or proposed edges |
| A | Admission | Validate candidates against CHI boundaries and contracts |
| T | Trace | Record provenance, hashes, receipts, paths, and causal lineage |
| P | Projection | Render admitted knowledge into UI, wiki, reports, or agent-visible summaries |
| R | Reconciliation | Resolve conflicts, stale claims, ambiguity, and revision events |
| C | Closure | Mark decisions, states, artifacts, or reasoning paths as closed with receipts |

The detailed CCGF chain is authoritative. The mnemonic is only a shorthand. It maps onto the chain's stages as follows:

| Letter | Covers | Note |
|---|---|---|
| G | Before the chain | The generative layer proposes candidates; its output enters the chain as Input. Outside CCGF. |
| A | Cognitive Router, DSN, Semantic Admission, Evidence Binding, Path Validation, Uncertainty Bounding | The router is A's entry: it routes and never admits. What "admitted" requires depends on the kind of object. |
| T | Every stage | Provenance, hashes, receipts, paths, and lineage are recorded at each stage. Not a stage of its own. |
| P | Projection | A revocable, rebuildable view. |
| R | Reconciliation | |
| C | Closure | |

The mnemonic lists T between A and P as a reading order: what is admitted must have been traced before it is projected. It does not mean tracing starts after admission.

Agents must not skip Admission, Trace, or Reconciliation when mutating knowledge. Because Trace is recorded at every stage, not skipping it means every stage emits its receipt.

---

## Five Boundaries

CCGF has exactly five governance boundaries:

1. 名界 — Semantic Admission
2. 據界 — Evidence Governance / Provenance
3. 徑界 — Path Governance / Causality
4. 幅界 — Uncertainty Governance / Envelope
5. 修界 — Revision Governance

Deterministic Semantics Narrowing (DSN) is not a sixth boundary. It is a core sub-mechanism inside 名界 / Semantic Admission.

Operational order:

```text
名 -> 據 -> 徑 -> 幅 -> 修
```

Priority:

```text
名界 > 據界
```

### Boundary Responsibilities

| Boundary | Responsibility | Failure Result |
|---|---|---|
| 名界 / Semantic Admission | Convert narrowed semantic candidates into typed, scoped, admissible semantic objects | Do not admit; return ambiguity, conflict, or denial |
| 據界 / Evidence Governance | Bind claims to provenance, authority, source, and receipts | Do not trust; mark unsupported or untrusted, and keep the claim pending |
| 徑界 / Path Governance | Validate causal, inferential, and dependency paths | Do not infer; mark path break or unauthorized leap |
| 幅界 / Uncertainty Governance | Bound confidence, scope, applicability, and ambiguity | Do not judge; mark needs revision and return bounded uncertainty |
| 修界 / Revision Governance | Reconcile contradiction, state change, revocation, and closure | Do not continue as stable knowledge |

Boundary behavior:

- If **名界** fails, do not proceed to evidence admission.
- If **據界** fails, do not trust or project the claim.
- If **徑界** fails, roll back to semantic admission.
- If **幅界** fails, trigger revision handling.
- If **修界** fails, do not continue the claim as current knowledge.

---

## Deterministic Semantics Narrowing (DSN)

### Canonical Position

DSN is the semantic stabilization engine of 名界.

```text
名界 / Semantic Admission
  -> Ambiguity Detection
  -> Candidate Semantic Mapping
  -> Context Binding
  -> Type Commitment
  -> Admission Gate
```

### DSN Rule

```text
No semantic narrowing, no admission.
```

Chinese form:

```text
未定其義，不可正其名。
```

### DSN Definition

Deterministic Semantics Narrowing is the deterministic narrowing function within 名界 that converts ambiguous, overloaded, or under-specified language into typed, bounded, admissible semantic objects before CHI permits evidence binding, inference, projection, or rendering.

### DSN State Model

All DSN outputs must use one of the following states:

| State | Meaning | Allowed Next Step |
|---|---|---|
| `NARROWED` | The term has been narrowed to a specific semantic object | Continue to Semantic Admission |
| `BOUNDED_AMBIGUOUS` | Multiple meanings remain, but they are bounded and explicit | Continue only with ambiguity annotation; do not hard-judge; evidence binds only under an ambiguity allowance |
| `UNRESOLVED` | The term cannot be narrowed with available context | Stop and request more context or mark pending |
| `CONFLICT` | Candidate meanings conflict with each other or with admitted state | Route to Revision Governance or adjudication |
| `DENIED` | The term is invalid, outside ontology, or unsafe to admit | Stop; do not admit |

### DSN Implementation Requirements

Agents implementing DSN must:

- Represent terms as structured semantic candidates, not raw strings.
- Preserve the original input text for auditability.
- Record candidate meanings considered.
- Record the narrowing basis: context, ontology, evidence, policy, source, or explicit user constraint.
- Assign a semantic type before admission.
- Assign a scope before admission.
- Emit a DSN receipt when a term becomes `NARROWED`, `BOUNDED_AMBIGUOUS`, `UNRESOLVED`, `CONFLICT`, or `DENIED`.
- Never silently coerce an ambiguous term into a single meaning.

### Ambiguity Allowance

Evidence may bind to a hyperedge that has a `BOUNDED_AMBIGUOUS` member only under an ambiguity allowance:

- It is granted by a human authority. A generative-layer agent, or the actor that proposed the binding, cannot grant one.
- It names the evidence, the hyperedge, the exact combinations of meanings the evidence is claimed to hold under (each combination assigns one remaining meaning to every ambiguous member), and a reason.
- It covers one binding only, and only the combinations it names.
- It is recorded as an `AMBIGUITY_ALLOW` receipt and referenced from the evidence binding.
- When a covered term is narrowed, combinations that no longer match are dropped. The allowance stays in force while a covered term is still ambiguous; once every covered term is narrowed the binding stands as an ordinary one if a granted combination still matches, and is voided if none does.
- It also lapses when a covered term's set of meanings changes, or when the evidence or hyperedge is revised or revoked.
- The hyperedge carries the ambiguity in its uncertainty envelope and is projected as `Bounded Ambiguous`.
- Without a valid allowance the binding is refused and the claim stays `PENDING`.
- If a lapsed allowance leaves a hyperedge without support, a `PENDING` one stays `PENDING` with `UNSUPPORTED` recorded, and an `ADMITTED` one becomes `CHALLENGED` and is withdrawn from projection.
- `UNRESOLVED`, `CONFLICT`, and `DENIED` terms never take evidence.

### Voiding an Evidence Binding

An evidence binding is never deleted. It is voided with a reason and a `REVISION_CLOSE` receipt, and a voided binding no longer counts for evidence governance.

- Dismissing a `CONTRADICTS` binding, which is what allows a challenged hyperedge to be reaffirmed, needs a human authority.
- The system voids a `SUPPORTS` binding automatically when its ambiguity allowance lapses.

### DSN Anti-Patterns

Do not:

- Treat LLM interpretation as deterministic narrowing.
- Use “most likely meaning” without recording alternatives and constraints.
- Bind evidence to an ambiguous term without an ambiguity allowance.
- Start path reasoning before semantic type commitment.
- Render a final answer from unresolved semantics.
- Promote DSN into a sixth boundary.

---

## Cognitive Router

The Cognitive Router classifies the type of cognitive work before DSN and admission.

Supported router lanes:

| Lane | Meaning | Typical Use |
|---|---|---|
| `D-R` | Deterministic-Reasoning | Formal rules, contracts, schemas, control logic |
| `E-X` | Evidence-Extraction | Documents, scans, citations, provenance extraction |
| `S-A` | Semantic-Admission | Ontology, term narrowing, entity typing, admission |
| `HYB` | Hybrid | Tasks requiring multiple governed modes |

The Cognitive Router is not an authority layer. It routes cognitive work into the correct governance path, but admission remains controlled by CCGF boundaries.

Router outputs must include:

```yaml
lane: string
reason: string
input_scope: string
expected_governance_path: list[string]
handoff_requirements: list[string]
```

---

## Agent Roles

### 1. Governance Architect Agent

Responsible for preserving CCGF doctrine and architectural integrity.

Must verify:

- Five Boundaries remain canonical.
- DSN remains inside 名界.
- Governance chain is not bypassed.
- Generated outputs are not treated as admitted knowledge.
- UI projection does not become authority.

### 2. DSN Agent

Responsible for semantic narrowing and type commitment.

Must produce:

- Semantic candidates
- Narrowing decision
- DSN state
- Semantic type
- Scope
- DSN receipt

Must reject or defer unresolved terms.

### 3. Evidence Agent

Responsible for evidence extraction, provenance, authority tiering, and evidence receipts.

Must distinguish:

- Raw source evidence
- Extracted evidence
- Summary
- Model-generated interpretation
- Admitted evidence

Model-generated text is never evidence by itself.

### 4. Path Validation Agent

Responsible for validating inference paths, causal paths, dependency paths, and recursive reasoning.

Must detect:

- Missing premise
- Unsupported inference
- Semantic drift
- Unauthorized leap
- Circular reasoning
- Broken dependency

### 5. Uncertainty Agent

Responsible for bounding confidence, scope, ambiguity, and applicability.

Must output:

- Confidence bound
- Scope bound
- Assumptions
- Known gaps
- Non-applicability conditions
- Required follow-up evidence when needed

### 6. Revision Agent

Responsible for contradiction, reconciliation, revocation, replacement, and closure.

Must handle state transitions such as:

```text
ADMITTED -> CHALLENGED -> UNDER_REVIEW -> REVISED -> CLOSED
ADMITTED -> REVOKED
PENDING -> ADMITTED
PENDING -> DENIED
PENDING -> UNDER_REVIEW
UNDER_REVIEW -> PENDING   (never admitted; boundaries re-run under a new receipt)
UNDER_REVIEW -> DENIED    (never admitted)
UNDER_REVIEW -> REVOKED
UNDER_REVIEW -> ADMITTED  (was admitted, challenge dismissed; reaffirmed under a new receipt)
```

`DENIED`, `REVOKED`, and `CLOSED` are terminal. Reopening a hyperedge or a semantic object, raising a revised candidate after a denial, or re-admitting revised content starts a new `CANDIDATE` that names the earlier one in its `predecessor_ids`; the earlier one is never resumed. The new candidate's id includes its predecessors, so identical content raised again gets a new id.

### 7. Projection Agent

Responsible for rendering admitted knowledge into UI, reports, API responses, dashboards, or documentation.

Must enforce:

```text
No Accord. No Coherence. No Render.
```

The Projection Agent must not render unadmitted claims as authoritative conclusions.

---

## Authority Model

Agents are workers, not authorities.

Agents may:

- Propose code changes.
- Draft contracts.
- Extract candidate facts.
- Build adapters.
- Add tests.
- Generate migration plans.
- Create candidate hyperedges.
- Produce implementation notes.

Agents must not:

- Admit evidence without CHI admission logic.
- Bypass SQLite authority stores.
- Treat generated text as ground truth.
- Project unadmitted claims into official views.
- Mutate ledger state without receipts.
- Invent provenance.
- Hide uncertainty.
- Replace deterministic checks with model judgment.
- Let adapters, UI components, agents, or model gateways become hidden authorities.

---

## System 1 / System 2 Separation

CHI separates generative and adjudicative roles.

| Layer | Role |
|---|---|
| System 1 | Generates candidates, hypotheses, summaries, code, and draft structures |
| System 2 | Performs structural adjudication, boundary enforcement, admission, trace, and revision |

Local models, remote models, Claude Code, Goose, OpenCode, Codex, or other assistants must be treated as **System 1 unless explicitly wired through CHI authority services**.

A model response is never evidence by itself.

---

## Admission States

Use explicit states. Do not rely on booleans when modeling governed cognition.

Recommended admission states:

```text
CANDIDATE
PENDING
ADMITTED
DENIED
CHALLENGED
UNDER_REVIEW
REVISED
REVOKED
CLOSED
```

A generated statement starts as `CANDIDATE`; it does not become `ADMITTED` until it passes the applicable CCGF gates. A semantic object is admitted by semantic admission alone; a hyperedge only after semantic admission, evidence governance, path governance, and uncertainty governance have all passed.

These are not admission states: `NARROWED`, `BOUNDED_AMBIGUOUS`, `UNRESOLVED`, and `CONFLICT` are DSN states; `UNKNOWN` and `NOT_PROJECTABLE` are projection labels; failure reasons (`UNSUPPORTED`, `UNTRUSTED`, `PATH_BREAK`, `NEEDS_REVISION`) are recorded on receipts.

---

## Data Modeling Rules

### Semantic Object Minimum Fields

A governed semantic object should include at minimum:

```yaml
id: string
type: string
label: string
original_text: string
scope: string
source_context: string | null
dsn_state: NARROWED | BOUNDED_AMBIGUOUS | UNRESOLVED | CONFLICT | DENIED
meanings: list[string]
narrowing_basis: object
admission_state: CANDIDATE | PENDING | ADMITTED | DENIED | CHALLENGED | UNDER_REVIEW | REVISED | REVOKED | CLOSED
created_at: timestamp
updated_at: timestamp
receipts: list[string]
predecessor_ids: list[string]
lineage_hash: string
```

### Evidence Object Minimum Fields

```yaml
id: string
source_id: string
source_type: string
authority_tier: string
provenance_uri: string | null
extracted_text: string | null
hash: string | null
valid_from: timestamp | null
valid_to: timestamp | null
supports: list[string]
contradicts: list[string]
receipt_id: string
```

### Receipt Minimum Fields

```yaml
id: string
receipt_type: string
subject_id: string
decision: string
basis: list[string]
actor: string
created_at: timestamp
hash: string | null
previous_receipt_id: string | null
```

Receipts should be append-only unless the local storage layer explicitly supports cryptographic replacement with traceable revocation.

---

## Evidence Doctrine

Evidence must be registered before use.

Minimum evidence metadata:

- Source identifier
- Content hash
- Ingest timestamp
- Scope
- Authority tier
- Provenance path
- Revision state
- Admission state

Evidence must be deterministic where possible:

- Deterministic chunking
- Stable IDs
- Stable hashes
- Versioned schemas
- Rebuildable indexes
- Repeatable ranking

Do not manually edit admitted evidence records unless the change itself is captured as a revision event.

Do not fabricate evidence, authority, citations, receipts, or audit history.

---

## Hypergraph Doctrine

CHI uses a hypergraph because many CHI relationships are n-ary, contextual, temporal, and governed.

Nodes are not enough. Binary graph edges are not enough.

Hyperedges may represent:

- Claims
- Obligations
- Risk relationships
- Control mappings
- Causal relationships

Every admitted hyperedge should preserve:

- Participating nodes
- Relation type
- Scope
- Evidence references
- Admission state
- Provenance
- Confidence or uncertainty envelope
- Revision lineage
- Receipt reference

---

## SQLite Authority Store

SQLite is acceptable and preferred for personal CHI when used as an authority-grade local datastore.

Use SQLite for:

- Evidence registry
- Hypergraph ledger
- Materialized state
- FTS5 retrieval
- Vector index coordination
- Graph/hyperedge traversal tables
- Receipts
- Migrations
- Deterministic rebuilds

Rules:

- Enable WAL where appropriate.
- Use schema versioning.
- Keep migrations deterministic.
- Make indexes rebuildable.
- Do not treat cache tables as authority tables.
- Do not bypass authority tables from UI or agent code.
- Admission state should be append-friendly and auditable.
- Prefer event/ledger records for governance transitions.
- Avoid destructive updates unless accompanied by revision receipts.
- Schema migrations must preserve prior decisions and receipts.
- An evidence receipt records the evidence record's content hash.
- A record in an admitted-or-later state must have its admission receipt, and every admission receipt must still have its record.
- A store must offer an integrity check that verifies the receipt chain, the evidence content hashes, and the rule above.
- Someone who can rewrite the whole database can rebuild the whole receipt chain; tamper-evidence against that needs the latest receipt id kept outside the database (not yet specified).

---

## Retrieval and Ranking

Retrieval is not admission.

A retrieved passage is only a candidate until admitted.

Ranking should prefer:

1. Authority tier
2. Scope match
3. Evidence quality
4. Semantic relevance
5. Deterministic tie-break

LLM reranking may only be used if it is routed through the configured CHI reranking model and bounded by CHI policy.

Do not introduce unmanaged local GGUF, node-llama, or ad hoc reranking paths if they violate policy.

---

## Projection Doctrine

Projection is rendering, not authority.

Projection targets may include:

- Obsidian wiki
- Markdown reports
- UI cockpit
- Draw.io diagrams
- JSON exports
- Graph views
- Human-readable summaries
- API response DTOs
- Dashboards

Projection rules:

- Only admitted knowledge may be rendered as accepted.
- Pending knowledge must be visibly pending.
- Denied knowledge must not appear as accepted.
- Conflict states must be visible.
- Provenance should be inspectable.
- Projection must be reproducible.
- Revoked claims must not appear in current-state projection.
- Ambiguous claims must render with uncertainty annotation or not at all.

Core rule:

```text
No evidence admission, no knowledge projection.
```

---

## UI Doctrine

The CHI UI is a governed projection layer.

It should be:

- Deterministic
- Declarative where possible
- Controlled at authority boundaries
- Fail-closed
- Inspectable
- English-only for NSS operator surfaces

The UI must not silently transform uncertain state into confident state.

Use explicit projection labels such as:

```text
Admitted
Pending Evidence
Bounded Ambiguous
Challenged
Revised
Revoked
Closed
Unknown
Not Projectable
```

Do not:

- Render raw model output as governed knowledge.
- Allow UI state to override admitted state.
- Hide uncertainty or ambiguity.
- Collapse `PENDING`, `CHALLENGED`, or `REVOKED` into generic success/failure labels.
- Display “secure,” “valid,” “compliant,” or “approved” without evidence and scope.

---

## Model Gateway Rules

Preferred model routing:

```text
Claude Code / Goose / OpenCode / Codex
        ↓
CHI Agent Gateway
        ↓
vLLM-MLX OpenAI-compatible endpoint
        ↓
CHI authority services
```

The Gateway forwards admitted calls directly to vLLM-MLX. LiteLLM and oMLX are legacy/inactive components of the local model stack — not part of the current gateway route. Do not reintroduce a routing layer between the Gateway and the model endpoint as part of the required path without a versioned doctrine change.

Rules:

- Agent tools should not talk directly to local model servers when CHI policy must be enforced.
- CHI Gateway handles policy, workspace admission, receipts, filesystem safety, tool safety, and forwarding to the configured model endpoint.
- Local inference servers (vLLM-MLX) manage inference lifecycle only.
- Model selection must not override CHI admission rules.
- Do not make local inference runtimes responsible for CHI policy.
- If a routing layer (e.g. LiteLLM) is ever reintroduced between the Gateway and the model endpoint, it must not be made responsible for CHI governance.
- Do not allow Claude Code, Goose, OpenCode, or Codex to bypass CHI Gateway for governed operations.

---

## Local Model Guidance

The personal CHI Platform may use local Apple Silicon models through MLX-compatible runtimes.

Expected roles:

| Role | Example |
|---|---|
| Local System 1 heavy context | Qwen / Gemma / MLX-compatible local model |
| System 2 canonical reasoning | Small reliable Qwen-class local model |
| Builder lane | Coder model |
| Embeddings | BGE-style embedding model |
| Reranking | Configured CHI reranking model only |

Do not hard-code one model as mandatory unless the repository contract requires it.

Use model aliases through the configured gateway where possible.

---

## MCP Doctrine

MCP is an interface, not an authority.

Canonical rule:

```text
MCP is the interface. CHI is the authority.
```

MCP servers may expose tools, resources, or workflows, but CHI must decide:

- Admission
- Policy
- Evidence state
- Projection eligibility
- Ledger mutation
- Receipt creation

Use split-server architecture where appropriate:

- Workspace/tool server
- Evidence/query server
- Projection/control server

Do not let an MCP adapter directly mutate authority state without a CHI governance transaction.

---

## Adapter Rules

Adapters translate external formats into CHI candidates.

Adapters do not admit knowledge.

Examples:

- QMD adapter
- Obsidian adapter
- Nessus adapter
- Schwab adapter
- MCP adapter
- Document parser
- Reranker adapter
- Model provider adapter

Adapter output should be:

```text
Candidate
EvidenceCandidate
ProjectionCandidate
HyperedgeCandidate
```

not:

```text
AdmittedEvidence
FinalKnowledge
TrustedFact
```

unless it has passed the relevant CHI authority.

---

## Coding Standards

### General

- Prefer deterministic functions for admission, narrowing, validation, and projection.
- Use typed schemas for all governance artifacts.
- Avoid hidden state in governance decisions.
- Every admission decision must be reproducible from inputs, context, policy, and receipts.
- Do not bury governance logic inside UI components.
- Do not let model output directly modify admitted state without a governance transaction.
- Keep modules small and auditable.
- Use explicit state machines.
- Use deterministic serialization.
- Use stable identifiers.
- Minimize hidden side effects.
- Separate authority, adapter, gateway, model, and projection code.

Prefer names that reveal authority role:

```text
EvidenceAuthority
AdmissionService
ProjectionAdmissionService
HypergraphLedger
MaterializedState
ReceiptStore
RevisionAuthority
ScopeMatcher
```

Avoid names that blur responsibility:

```text
SmartManager
AIProcessor
KnowledgeMagic
AutoDecider
UniversalAgent
```

### Python

- Use type hints for public functions.
- Use Pydantic or dataclasses for governance objects.
- Keep pure governance logic separate from API, CLI, and UI adapters.
- Write tests for state transitions and rejection paths, not only happy paths.

### TypeScript

- Use Zod or equivalent runtime validation for API boundaries.
- Do not use `any` for governed objects.
- Keep projection types separate from authority-state types.
- UI components must consume projection DTOs, not raw model output.

---

## Repository Organization Guidance

Recommended structure for a CCGF implementation:

```text
ccgf/
  router/
  dsn/
  semantic_admission/
  evidence/
  path_validation/
  uncertainty/
  revision/
  projection/
  receipts/
  schemas/
  tests/
  docs/
```

Recommended platform structure may include:

```text
chi/
  gateway/
  dea/
  kga/
  hypergraph/
  retrieval/
  adapters/
  mcp/
  models/
  ui/
  migrations/
  receipts/
  tests/
  docs/
```

Recommended module boundaries:

- `router/` decides cognitive lane.
- `dsn/` narrows language into semantic candidates and semantic objects.
- `semantic_admission/` admits, denies, or marks semantic objects pending.
- `evidence/` binds claims to source authority and provenance.
- `path_validation/` validates inference and dependency chains.
- `uncertainty/` bounds confidence, scope, and applicability.
- `revision/` manages contradiction, revocation, replacement, and closure.
- `projection/` produces render-safe DTOs.
- `receipts/` records governance decisions.
- `schemas/` defines canonical governed objects.
- `gateway/` enforces workspace, tool, filesystem, and model-routing policy.
- `adapters/` converts external inputs into candidates, not admitted state.

---

## Agent Workspace Safety

Agents must respect workspace boundaries.

Allowed by default:

- Reading repository files.
- Proposing patches.
- Creating tests.
- Running local test commands.
- Updating documentation.
- Creating migration drafts.
- Creating non-authority generated artifacts.

Requires explicit care:

- Database migrations.
- Ledger writes.
- Schema changes.
- Deleting files.
- Modifying authority state.
- Changing model routing.
- Changing security policy.
- Changing admission logic.

Forbidden unless explicitly requested and safe:

- Removing provenance fields.
- Disabling tests to pass builds.
- Replacing deterministic checks with model calls.
- Writing secrets into the repository.
- Committing API keys.
- Bypassing CHI Gateway policy.
- Treating generated summaries as admitted evidence.

---

## Standard Agent Workflow

For non-trivial work, follow this loop:

```text
1. Inspect
2. Classify through the Cognitive Router
3. Identify authority boundary
4. Locate contracts and tests
5. Propose change
6. Implement minimally
7. Add or update tests
8. Run verification
9. Report what changed, what passed, and what remains uncertain
```

Do not implement broad rewrites when a bounded patch is sufficient.

---

## Testing Requirements

Every CCGF module must include tests for:

1. Successful governed path
2. Ambiguous input
3. Missing evidence
4. Broken inference path
5. Out-of-scope claim
6. Contradictory evidence
7. Revision or revocation
8. Projection denial

### Required DSN Tests

- Ambiguous term with a known, explicit, finite set of remaining meanings becomes `BOUNDED_AMBIGUOUS`; a term for which no such set can be established becomes `UNRESOLVED`.
- Invalid term becomes `DENIED`.
- Conflicting meanings become `CONFLICT`.
- Narrowed term records candidate alternatives.
- Evidence binding fails if DSN state is not `NARROWED` or `BOUNDED_AMBIGUOUS` with a valid ambiguity allowance.
- An ambiguity allowance recorded by a generative-layer actor, or by the actor that proposed the binding, is refused.
- An ambiguity allowance covers only its own binding and only the combinations it names.
- An ambiguity allowance lapses when a covered term's set of meanings changes, and when the evidence or hyperedge is revised or revoked.
- When a covered term is narrowed, combinations that no longer match are dropped; the binding stands as an ordinary one if a granted combination remains and every covered term is narrowed, and is voided if none remains.
- A hyperedge left without support by a lapsed allowance stays `PENDING` if it was pending and becomes `CHALLENGED` if it was `ADMITTED`.
- An evidence binding is never deleted: voiding records a reason and a `REVISION_CLOSE` receipt, and a voided binding does not count for evidence governance.
- Dismissing a `CONTRADICTS` binding by anyone other than a human authority is refused.
- A hyperedge with allowance-bound evidence carries the ambiguity in its uncertainty envelope and projects as `Bounded Ambiguous`.
- `UNRESOLVED`, `CONFLICT`, and `DENIED` terms never take evidence, allowance or not.

### Required Projection Tests

- Unadmitted claim does not render as fact.
- Ambiguous claim renders with uncertainty annotation or not at all.
- Revoked claim does not appear in current-state projection.
- Projection contains receipt references where required.

### Required Platform Tests

Include tests for:

- Admission success.
- Admission denial.
- Pending state.
- Conflict state.
- Missing provenance.
- Scope mismatch.
- Revision trigger.
- Deterministic IDs.
- Rebuildable index behavior.
- Projection exclusion of unadmitted claims.
- Gateway policy rejection.
- Adapter output remaining candidate-only.
- Retrieval ranking preserving authority tier before relevance.

Use fixtures with stable hashes and deterministic expected outputs.

---

## Verification Commands

Use the commands defined by the repository.

If unavailable, prefer this order:

```bash
# Python
python -m pytest

# Python linting / typing, if configured
ruff check .
mypy .

# Frontend
npm test
npm run lint
npm run typecheck
npm run build

# Playwright, if configured
npx playwright test
```

Do not claim verification passed unless the command actually ran and passed.

If verification cannot run, state why.

---

## Git Behavior

Before edits:

```bash
git status
```

After edits:

```bash
git diff
```

Commit only when the user explicitly requests it.

Do not create large commits that mix unrelated authority, UI, model, and documentation changes.

Recommended commit style:

```text
area: concise change summary
```

Examples:

```text
dea: add deterministic scope mismatch tests
kga: introduce hyperedge revision receipt
ui: render conflict state in projection table
docs: add CHI agent authority rules
```

---

## Documentation Rules

When documenting CHI or CCGF:

- Use CCGF, not Aegis.
- Use CHI as the platform name.
- Keep Five Boundaries as five boundaries.
- State explicitly that DSN is inside 名界, not a sixth boundary.
- Preserve the governance law exactly unless a versioned doctrine change is approved.
- Distinguish between candidate, admitted, revised, revoked, and closed knowledge.
- Do not describe CHI as ordinary RAG.
- Do not describe CHI as an unconstrained agentic workflow.
- Describe CHI as a contract-governed cognitive governance architecture.
- Include authority boundaries.
- Include failure behavior.
- Avoid vague claims such as “AI decides,” “system understands,” or “knowledge is generated.”
- Prefer “candidate,” “admitted evidence,” “projection,” “receipt,” “semantic object,” and “authority.”

Recommended phrase:

```text
CCGF governs not only what the system may say, but what it may know, infer, revise, and render.
```

---

## Security and Assurance Rules

CHI and CCGF are intended for high-assurance use, including aerospace, RMF, NIST, IL5/IL6, and national-security-style workflows.

Agents must default to fail-closed behavior.

Fail closed when:

- Semantics are unresolved.
- Evidence is missing.
- Provenance is unknown.
- Inference path is broken.
- Scope is exceeded.
- Contradictory evidence is unresolved.
- Projection authority is absent.
- State is stale, invalid, or unverified.

Preferred failure states:

```text
Pending
Denied
Unknown
Conflict
Needs Revision
Not Projectable
```

Avoid unsafe defaults such as:

```text
Admitted
Valid
Current
Trusted
Renderable
```

unless explicitly proven.

For NIST/RMF work, controls, findings, evidence, and implementation statements must retain source traceability.

---

## Handling Ambiguity

When ambiguity affects authority, do not guess.

Use explicit states:

```text
Unresolved
Bounded Ambiguous
Conflict
Pending
Needs User Decision
```

When ambiguity does not affect safety or authority, make the smallest reasonable assumption and document it.

---

## Agent Task Checklist

Before completing a CCGF-related task, an agent must answer:

```text
1. Did I preserve the Five Boundaries?
2. Did I keep DSN inside 名界 rather than creating a sixth boundary?
3. Did I avoid reasoning over raw words?
4. Did I distinguish generated candidates from admitted knowledge?
5. Did I require evidence before trust?
6. Did I validate the inference path?
7. Did I bound uncertainty and scope?
8. Did I support revision, revocation, or closure?
9. Did I prevent raw model output from becoming UI authority?
10. Did I leave receipts or testable artifacts for governance decisions?
```

Before completing a platform-related task, also answer:

```text
11. Did I preserve SQLite / ledger authority boundaries?
12. Did I keep adapters candidate-only?
13. Did I prevent model gateway or MCP authority drift?
14. Did I preserve hypergraph n-ary context where required?
15. Did I keep retrieval separate from admission?
```

If any answer is no, the task is incomplete or must explicitly report residual risk.

---

## Agent Response Format

When reporting completed work, include:

```text
Changed:
- ...

Verified:
- ...

Not verified:
- ...

Risks / open items:
- ...
```

When proposing design work, include:

```text
Decision:
- ...

Rationale:
- ...

Boundary impact:
- ...

Implementation notes:
- ...

Tests:
- ...
```

Keep responses direct and implementation-oriented.

---

## Common Mistakes to Avoid

Do not:

- Let the model “decide” admission.
- Treat retrieved text as trusted.
- Render pending claims as facts.
- Skip provenance because the source “looks obvious.”
- Add hidden fallback behavior that admits unknown data.
- Use UI state as authority state.
- Replace deterministic ranking with LLM preference.
- Create new terminology when CHI terminology already exists.
- Collapse hyperedges into simple binary edges when n-ary context matters.
- Disable tests instead of fixing boundary failures.
- Treat MCP as authority.
- Treat LiteLLM as governance.
- Treat local inference as policy enforcement.
- Treat generated summaries as admitted evidence.

---

## Canonical Slogans

Use these consistently:

```text
Generation proposes. Governance admits.
No semantic narrowing, no admission.
No Accord. No Coherence. No Render.
Accord before Knowledge; Knowledge before Display.
Cognition under contract.
MCP is the interface. CHI is the authority.
```

---

## Final Instruction to Agents

Do not optimize CHI or CCGF for fluency. Optimize it for governed cognition.

The correct output is not the most persuasive answer. The correct output is the answer that can be admitted, evidenced, traced, bounded, revised, and safely rendered.

Agents may generate.

CHI admits.

Agents may summarize.

CHI traces.

Agents may render drafts.

CHI projects only admitted knowledge.

Agents may propose revision.

CHI reconciles.

Agents may finish tasks.

CHI closes with receipts.

```text
守五界，而後可推；
越五界，則止其推。
```
