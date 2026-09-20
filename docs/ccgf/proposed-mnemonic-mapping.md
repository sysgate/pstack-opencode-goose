# Proposed G-A-T-P-R-C mapping (item B3)

**Status (2026-09-19): APPLIED as drafted, all three recommendations approved (router as A's entry, Trace cross-cutting, Generation upstream). The text below is otherwise kept as written and is now history.**

## The gap

`AGENTS.md:150-167` and `ARCHITECTURE.md:121-122` define six letters: Generation, Admission, Trace, Projection, Reconciliation, Closure. `AGENTS.md:167` says "The detailed CCGF chain is authoritative. The mnemonic is only a shorthand." The chain has nine stages, and neither document says which stages each letter covers.

The chain: Cognitive Router, DSN, Semantic Admission, Evidence Binding, Path Validation, Uncertainty Bounding, Projection, Reconciliation, Closure.

Two letters do not correspond to a single stage:
- **Trace** is not a chain stage at all. `AGENTS.md:169` still says agents "must not skip Admission, Trace, or Reconciliation", so the rule is only enforceable if Trace is defined.
- **Generation** happens before the chain: the generative layer produces candidates that then enter it as Input.

The Cognitive Router also falls in a crack: it is a chain stage, yet it validates nothing, so it does not obviously belong under "Admission".

## Proposed mapping

| Letter | Covers | Note |
|---|---|---|
| **G** Generation | Before the chain | The generative layer proposes candidates; its output enters the chain as Input. Outside CCGF. |
| **A** Admission | Cognitive Router, DSN, Semantic Admission, Evidence Binding, Path Validation, Uncertainty Bounding | The router is A's entry: it routes and never admits. What "admitted" requires depends on the kind of object (ADR 0002). |
| **T** Trace | Every stage | Provenance, hashes, receipts, paths and lineage are recorded at each stage. Not a stage of its own. |
| **P** Projection | Projection | A revocable, rebuildable view (D8). |
| **R** Reconciliation | Reconciliation | |
| **C** Closure | Closure | |

The mnemonic lists T between A and P because what has been admitted must have been traced before it is projected. That is a reading order, not a claim that tracing starts after admission.

## Doctrine edits this would make

| Where | Change |
|---|---|
| `AGENTS.md` after line 167 (all 4 copies) | Add the mapping table and one sentence: Trace is recorded at every stage, so "must not skip Trace" means every stage emits its receipt |
| `ARCHITECTURE.md` after the mnemonic (line 122) | The same table |
| `docs/ccgf/CONTEXT.md` | New term Trace; the Governance chain entry says what each letter covers |

## Not touched, and a note

`chi-platform/AGENTS.md` uses `G0` to `G6` for the Goose engineering loop (`G0 Goal Admission`, `G6 Receipt`). That is a developer workflow, unrelated to the chain, but it reuses the letter G and the word "Admission". I recommend leaving it: it lives in a separate section of a separate project's file, and renaming it is outside this mapping.

## Decisions for you (recommendation first)

1. **Router as A's entry, or unmapped?** Recommend A's entry: it comes after Generation and before DSN, and leaving it unmapped would make the mnemonic silently skip a stage.
2. **Trace as cross-cutting, not a stage?** Recommend yes: it matches "Record provenance, hashes, receipts, paths, and causal lineage" and the fact that every boundary already emits a receipt.
3. **Generation as upstream of the chain, outside CCGF?** Recommend yes: it matches "Generation proposes. Governance admits.", and the generative layer is by definition not an authority.
