# White paper discrepancies against the accepted doctrine (item C1)

**Status (2026-09-19): APPLIED. L1 and L2 went into `ARCHITECTURE.md` §7, the Revision Agent list in all four `AGENTS.md` copies and the glossary's Lineage entry; then W1 to W5 were patched into the white paper itself (decision 3: direct patch of `word/document.xml`).**

How the white paper was patched: backup first (`CCGF_White_Paper_v2_0_Formal_Architecture_Edition.docx.backup-before-doctrine-sync-20260919`, next to the original, byte-identical to it before the edit); edited with `lxml` after confirming a parse-and-reserialize reproduced the original bytes; built in the scratchpad and verified before replacing the file (zip integrity, all 18 other parts byte-identical, XML well-formed, 25 tables before and after, and a text diff showing only the five intended changes). No renderer (Word or LibreOffice) is available here, so page layout was not viewed.

What was actually changed, with two differences from the proposed text below: (1) **W1**: the hyperedge example block now shows `relation_type, members, scope, validity, uncertainty_envelope, admission_state, receipt, lineage` plus a separate evidence-binding block, and the paragraph after it gained two sentences (evidence is bound separately and never a member; a chain of hyperedges is a hyperpath); the two sentences went into the following paragraph because the block itself is code-styled. (2) **W4**: only `admission.status` changed (added `UnderReview`); `dsn.state` already listed all five DSN states, so nothing was needed there, and the sketch's CamelCase spelling was kept. **W2** was finalized with L1 and L2: the `Generated` row was removed, an `Under Review` row added, and the Typical Transition column rewritten to match `ARCHITECTURE.md` §7. **W3** and **W5** are as proposed.

Not changed: M1, M2, M3 (minor or outside the decisions), the paper's own status line ("Architecture Draft - Canonical Doctrine Candidate") and date (June 19, 2026), and no revision note was added to the paper.

One scoping choice made while applying L2: the reopening rule is worded for hyperedges only, because `HyperedgeRecord` has a `lineage_hash` and `SemanticObject` has no lineage field. That was resolved afterwards by `proposed-lineage-for-semantic-objects.md`: the rule now covers both kinds through `predecessor_ids`, and the white paper's wording ("a new Candidate linked by lineage") is consistent with it.

Source read: `CCGF_White_Paper_v2_0_Formal_Architecture_Edition.docx`, all 337 lines of extracted text (extracted to the session scratchpad; the `.docx` itself was not opened for writing). Its own status line reads "Architecture Draft - Canonical Doctrine Candidate", dated June 19, 2026, so it predates every decision recorded in `docs/ccgf/` (D1 to D10, ADRs 0001 and 0002, the state vocabulary, relation types and roles, the ambiguity allowance, the mnemonic mapping).

Section numbers below are the paper's own.

## Facts about the file

- No tracked changes, no comments or footnotes, and no Word lock file, so it is not open anywhere.
- `python-docx` is not installed. An edit would either patch `word/document.xml` directly or first install the library into the Anaconda Python (a change to your environment that I would ask about).
- This folder is not a git repository, so a backup copy is the only undo.

## A. Contradicts a decision you accepted (5 places)

**W1. §9, the hyperedge example.** It reads `{ claim, narrowed_semantic_object, evidence_set, source_authority, policy_scope, inference_path, uncertainty_envelope, admission_state, receipt }`. Against the accepted doctrine:
- `evidence_set` is a member-like part of the hyperedge; ADR 0001 says evidence is bound to it, never a member.
- `source_authority` belongs to the evidence record (its authority tier), not the hyperedge.
- `inference_path` is a hyperpath, a run of hyperedges, not a field of one.
- `policy_scope` is the hyperedge's `scope`; `claim` is the relation type `CLAIM`; `narrowed_semantic_object` is a member with a role.
- Only `uncertainty_envelope`, `admission_state` and `receipt` match as written.

**W2. §8, the state table.** Nine states and transitions, compared with the applied vocabulary:
- `Generated` is a state; the applied list has no `GENERATED` (a generated statement is a `CANDIDATE`).
- `UNDER_REVIEW` is absent.
- Transitions the applied machine does not have: `Candidate → Admitted` directly (skipping `Pending`), `Admitted → Projected` (projection is a derived view, D8, not a state), `Challenged → Reaffirmed` (no such state), `Revised → Admitted`, `Denied → revised candidate`, `Revoked → Closed`, `Closed → Reopened`.
- Two of these are real lifecycle behaviors the applied machine lacks: see L1 and L2.

**W3. §4.2, step 5 "Admission Gate", Output column.** "Admitted, pending, denied, or unresolved state." `unresolved` is a DSN state, not an admission state.

**W4. Appendix A, the schema sketch.** `admission.status` lists eight values with no `UNDER_REVIEW` and a `Candidate` start that matches, but the field spelling (`Narrowed`, `BoundedAmbiguous`) differs from the doctrine's uppercase enums. The sketch keeps `evidence` as a separate top-level array, which is consistent with ADR 0001.

**W5. §4.3, the "Bounded Ambiguous" row.** "May be displayed as ambiguity; may not be forced into final judgment." It says nothing about evidence. The doctrine now says evidence binds only under an ambiguity allowance, and the `Denied` row already says "do not bind evidence".

## B. Gaps in the applied doctrine that the paper exposes

**L1. A dismissed challenge has no way back to `ADMITTED`.**
- The paper's §8 has `Challenged → Reaffirmed`. In the state machine now in `ARCHITECTURE.md` §7 (and in the Revision Agent list in `AGENTS.md`), the only edge into `ADMITTED` is from `PENDING`. A hyperedge that is `CHALLENGED` and then found sound can only end up `REVISED`, `REVOKED`, or, if never admitted, `PENDING` or `DENIED`.
- This gap was in the original §7 as well as in my rewrite of it; I did not catch it then.
- Recommend: add `UNDER_REVIEW → ADMITTED` labelled "challenge dismissed, reaffirmed under a new receipt". "Reaffirmed" is an outcome on the receipt, not a new state.

**L2. Terminal states and reopening.** The paper lets `Revised → Admitted`, `Denied → revised candidate`, and `Closed → Reopened only by formal trigger`. The applied machine treats `DENIED`, `REVOKED` and `CLOSED` as terminal, which fits the append-only rule (`ARCHITECTURE.md:387`, "destructive updates without receipts are forbidden").
- Recommend: keep them terminal, and express the paper's intent as a **new candidate linked by lineage**: reopening, a revised candidate after denial, and re-admitting revised content all start a new `CANDIDATE` whose `lineage_hash` points at the earlier hyperedge.
- The "Reopened" node in `diagrams/ccgf-chain.html`, which I had listed as unreviewed, comes from this paper's `Closed → Reopened` line. Under the recommendation it would be relabelled or drawn as a new candidate; I have not opened the diagram file for editing.

## C. Minor, or outside the decisions made

- **M1. §3, Path row:** "No inference; path rejected." The doctrine says a path failure rolls back to 名界 (`PATH_BREAK`).
- **M2. §5, lane D-R:** the paper expands it as "Deterministic Retrieval / Deterministic Reasoning"; `AGENTS.md` says "Deterministic-Reasoning". Not part of the hypergraph work.
- **M3. §1.1 and §11 (Receipts):** projections "should produce an auditable receipt". `ARCHITECTURE.md` §9.1 has no projection receipt type, and projection is a rebuildable view. Left undecided; recommend leaving the paper's wording, since a record of what was shown is not the same as authority.

## D. Consistent with the accepted doctrine (nothing to change)

The core thesis and axioms; the Five Boundaries and DSN as part of 名界; the router lanes and placement; the full chain (§5.1 and §6, which match the nine-stage chain word for word); the DSN state model except W5; the DSN operating steps; requirements on DSN auditability (matches D6) and router traceability; the test gates; the canonical language table.

## Proposed replacement text (for W1, W3, W4, W5; W2 waits on L1 and L2)

- **W1:** "Hyperedge Example: { relation_type, members: [semantic objects, each with a role], scope, validity, uncertainty_envelope, admission_state, receipt, lineage }. Evidence is bound to the hyperedge separately, each binding recording the evidence record, whether it supports or contradicts, and its receipt; each evidence record carries its own source authority. A conclusion reached by chaining hyperedges is a hyperpath, not a field of one hyperedge."
- **W3:** "Admission state (pending, admitted, or denied), with the DSN state recorded."
- **W4:** `admission.status` gets the nine admission states; `dsn.state` lists all five DSN states.
- **W5:** append "Evidence binds only under an ambiguity allowance."

## Decisions for you (recommendation first)

1. **Add `UNDER_REVIEW → ADMITTED` for a dismissed challenge (L1)?** Recommend yes. It changes `ARCHITECTURE.md` §7, the Revision Agent list in `AGENTS.md` (4 copies) and the paper's §8.
2. **Keep `DENIED`, `REVOKED` and `CLOSED` terminal, and express reopening as a new candidate linked by lineage (L2)?** Recommend yes.
3. **How to edit the `.docx`?** Recommend patching `word/document.xml` directly after making a backup: it keeps all formatting, needs no new software, and I would verify by re-extracting the text and diffing it against this report. The alternatives are installing `python-docx` (changes your Anaconda environment) or leaving the paper untouched and adding a note that it is superseded on these points.
