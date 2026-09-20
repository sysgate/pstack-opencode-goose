# Proposed doctrine edits

**Status (2026-09-19): section A is APPLIED (A1 to A6). B1, B2 and B5 are APPLIED through `proposed-state-vocabulary.md`. B4 is APPLIED through `proposed-ambiguity-allowance.md`. B6 and B7 are APPLIED through `proposed-relation-types-and-roles.md`. B3 is APPLIED through `proposed-mnemonic-mapping.md`. C (the white paper `.docx`) is APPLIED through `whitepaper-discrepancies.md`, so every item in this file is now applied and nothing in them has been applied.** `AGENTS.md` and `docs/ARCHITECTURE.md` are governing doctrine; B and C change them only after you approve each item.

**Line numbers below were taken before section A was applied and are now stale.** Shifts: in all four `AGENTS.md` copies, lines after 577 moved up by 1 (so the old 1029 is now 1028; old 279 and 270 are unchanged); in `ARCHITECTURE.md`, lines after old line 130 moved down by 2 and lines after old line 279 by 4 (so the old 367 is now 371; the A6 edit changes line 194 in place and moves nothing). Search by text, not by number. The pre-edit files are backed up in the session scratchpad (`doctrine-backup/`); this folder is not a git repository, so there is no other history.

The decisions referenced (D1 to D10) are the ones recorded in `docs/ccgf/CONTEXT.md`, `docs/ccgf/docs/adr/` and the domain-modeling entries in `MAP.md`:

| Ref | Decision |
|---|---|
| D1 | "Hyperedge" means admitted only; before that it is a hyperedge candidate |
| D2 | Evidence is bound to a hyperedge, never a member (ADR 0001) |
| D3 | "Semantic object" means admitted only; before that it is a semantic candidate |
| D4 | Bounded ambiguity = a known, explicit, finite set of remaining meanings; unresolved = no such set could be established |
| D5 | Evidence binds to narrowed terms; to bounded-ambiguous ones only under a recorded allowance |
| D6 | Narrowing is deterministic when it rests on a recorded basis, never a model's most probable reading alone |
| D7 | Admission depends on the kind: semantic object by 名界 alone, hyperedge by all four boundaries (ADR 0002) |
| D8 | Projection is a revocable, rebuildable view; chain order is unchanged |
| D9 | Authority tier 4 is tracked, never admitted evidence, never sufficient for 據界 |
| D10 | "Chain" is the governance sequence; a run of hyperedges is a hyperpath |

## Where the text lives

| File | Copies |
|---|---|
| `AGENTS.md` | Root, `chi/AGENTS.md` and `AGENTS_combined.md` are byte-identical. `chi-platform/AGENTS.md` has the same passages at the same line numbers plus a Goose section appended at line 1285 (1390 lines vs 1350). |
| `docs/ARCHITECTURE.md` | One copy. |
| White paper | `CCGF_White_Paper_v2_0_Formal_Architecture_Edition.docx`, one copy. |

The root `CLAUDE.md` says `AGENTS.md` is duplicated verbatim in `chi/AGENTS.md`; that holds for the root and `chi/` copies but not for `chi-platform/`. Apply each `AGENTS.md` edit to all four copies, as a patch to `chi-platform/` rather than a file copy so its Goose section survives.

## A. Follows directly from decisions you already made

Each item is a wording change with no new design.

**A1. `AGENTS.md:1025`** (D4)
- Now: `Ambiguous term becomes BOUNDED_AMBIGUOUS when context is insufficient.`
- Proposed: `Ambiguous term with a known, explicit, finite set of remaining meanings becomes BOUNDED_AMBIGUOUS; a term for which no such set can be established becomes UNRESOLVED.`
- Why: today's text contradicts the state table at `AGENTS.md:256` (UNRESOLVED = cannot be narrowed with available context).

**A2. `AGENTS.md:573-584`** (D2)
- Remove `- Evidence support` from "Hyperedges may represent". Evidence attaches through bindings.
- Related and not decided here: the other ten entries do not match the five `relation_type` values in `ARCHITECTURE.md` §9.1 (see B6).

**A3. `docs/ARCHITECTURE.md` §9.1, under the `hyperedges` and `semantic_objects` schemas** (D1, D3)
- Add a note: `These tables also hold candidates and unadmitted terms. Only ADMITTED rows (and later REVISED or REVOKED ones) are hyperedges or semantic objects in the sense of §8.2.`
- Why: §8.2 defines ℰ as admitted hyperedges, while the table stores CANDIDATE and PENDING rows.

**A4. `docs/ARCHITECTURE.md` after the fail-closed matrix (line 129)** (D8)
- Add: `Projection is a derived, rebuildable view of admitted knowledge that is not under challenge. A claim challenged or revoked after projection is withdrawn from it; the chain order does not change.`
- Why: the chain projects before reconciliation, yet the matrix excludes revoked claims from projection.

**A5. `docs/ARCHITECTURE.md:367`, Tier 4** (D9)
- Append: `Tier 4 records are tracked as candidates. They are never admitted evidence and never satisfy 據界 alone.`
- Why: §9.2 lists model outputs under evidence tiers while the core rule says generated text is never evidence.

**A6. `docs/ARCHITECTURE.md` §7, above the state diagram (line ~194)** (D7)
- Add: `This state machine describes hyperedges (claims). A semantic object is governed by its DSN state and semantic admission (名界) alone; NARROWED here is a DSN state, not an admission state.`

## B. Needs a decision first

These came up while modeling. The docs contradict themselves or say nothing, and I have not made the choice for you. My recommendation is listed first.

**B1. Failure-state names (three conflicting sets)**
- Where: `AGENTS.md:199-205` (prose), `ARCHITECTURE.md` §2 table (lines 45-49) and the §4 matrix (lines 124-128).
- Recommend: make the §4 matrix canonical (`DENIED/PENDING`, `PENDING/UNTRUSTED`, `PATH_BREAK`, `NEEDS_REVISION`, `REVOKED/UNSTABLE`), and have the §2 table and the `AGENTS.md` prose refer to it. It is the most operational of the three.

**B2. The §7 state machine against §4 and the schemas**
- Line 203 sends a narrowed object to `DENIED` on evidence or path failure, while §4 and `AGENTS.md:211` say path failure rolls back to 名界.
- `CHALLENGED`, `UNDER_REVIEW`, `CLOSED`, `UNKNOWN` and `NOT_PROJECTABLE` are used in §7 but are not in the §9.1 `AdminState` enums.
- Recommend: after A6, make the hyperedge machine use only states that exist in the §9.1 hyperedge enum, and add the missing ones to that enum (`DENIED` is missing from hyperedges, `CHALLENGED` from semantic objects). Then the schema is the single source.

**B3. G-A-T-P-R-C mapping (`ARCHITECTURE.md:118`)**
- The mnemonic has 6 letters against 9 chain stages, and Trace is not a stage.
- Recommend adding: `G = generation upstream of the router (System 1, outside CCGF); A = DSN through uncertainty bounding; T = receipts recorded at each stage (cross-cutting); P = projection; R = reconciliation; C = closure.` This is my inference, not something either document states, so it needs your approval.
- Also noted: `chi-platform/AGENTS.md` uses `G0`-`G6` for Goose loop steps (`G0 Goal Admission`, `G6 Receipt`), which is unrelated but overlaps the letter G and the word "Admission".

**B4. Recorded allowance for bounded ambiguity (D5)**
- Edits to `AGENTS.md:279` (`Bind evidence to an ambiguous term`), `AGENTS.md:1029`, `ARCHITECTURE.md:72` (only `NARROWED` "Admissible to 據界") and `ARCHITECTURE.md:79` would reference a "recorded allowance", but nothing defines who records it or what it contains.
- Recommend: hold these edits until the mechanism is specified. Otherwise the doctrine would cite an undefined thing. The interim risk is that the four places still contradict each other.

**B5. DSN receipt for `UNRESOLVED` (`AGENTS.md:270`)**
- The receipt list covers `NARROWED`, `BOUNDED_AMBIGUOUS`, `CONFLICT`, `DENIED` but not `UNRESOLVED`, so an unresolvable term leaves no audit trace and a repeated attempt cannot be told from a first one.
- Recommend: add `UNRESOLVED` to the list. Fail-closed and auditable both point that way, and the cost is one more receipt type.

**B6. Relation types**
- `AGENTS.md` lists 11 things a hyperedge may represent; §9.1 has 5 `relation_type` values (`CLAIM`, `OBLIGATION`, `RISK_CONTROL`, `CAUSAL_PATH`, `REVISION_EVENT`); the §8.1 diagram uses `CONTRACTUAL_OBLIGATION`.
- Recommend: state that the §9.1 list is the current set and extensible, and have `AGENTS.md` list only kinds that map to a value.

**B7. Role vocabulary**
- §8.2 has 7 roles (`SUBJECT`, `OBJECT`, `PREDICATE`, `CONDITION`, `SCOPE_QUALIFIER`, `BENEFICIARY`, `ASSUMPTION`); §9.1 `HyperedgeMember.role` has 5 (with `QUALIFIER`); the §8.1 diagram uses Debtor and Target.
- Recommend: the 7-role list as the schema enum, and the diagram's Debtor and Target described as relation-type-specific labels for `SUBJECT` and `OBJECT`.

## C. Not editable by me without your call

**C1. White paper example (§9 of the docx)**
- Its hyperedge example lists `evidence_set`, `source_authority`, `policy_scope` and `inference_path` as parts of the hyperedge, which D2 rejects.
- Proposed: rewrite the example to show members and bindings separately.
- A `.docx` edit is a separate step; say if you want it done with the docx tooling.

## Suggested order

1. Approve A1 to A6: small, no new design.
2. Decide B1, B2 and B5: a fail-closed state vocabulary that every table then shares.
3. Specify the recorded allowance (B4) as its own piece of work before touching the four places that mention it.
4. Leave B3, B6 and B7 for after the state vocabulary settles.
