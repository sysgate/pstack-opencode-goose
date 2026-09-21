# The store's lifecycle facts: what a changed or removed claim may do

Type: research
Status: in progress (research subagent, started at charting)
Blocked by:

## Question

When the source text of a loaded glossary claim changes or disappears, what does the store as it exists today allow, who may do it, and where can it be made atomic? Establish it from primary sources only: the doctrine (`docs/ARCHITECTURE.md`, the state machine and the revision sections; `AGENTS.md`) and the code and schema under `chi-platform/infra/chi_agent_gateway/app/hypergraph/` (the SQL triggers in the migrations, `hyperedges.py`, `objects.py`, `evidence.py`, `bindings.py`, `admission.py`, `glossary.py`).

Cover:
- Every **legal state transition** for hyperedges, semantic objects and candidate evidence, the trigger that guards each, the receipt type it needs, and which actor kinds (`human:`, `sys:`, `adapter:`) may perform it.
- What `revoke`, `reopen` and `void` actually do: the ids they create, how `predecessor_ids` and `lineage_hash` are recorded, and what cascades when evidence is revoked (bindings voided, hyperedge challenged or left unsupported).
- What `challenge` and `under review` require, and whether a machine actor may challenge a hyperedge (the map's standing principle is that a machine may only make the store less assertive).
- What today's glossary loader does at each step, and what it never does.
- **Atomicity**: which operations run in one hypergraph transaction and which use a separate connection (the candidate-evidence insert does). What state a crash between the two leaves behind.

Read-only. Change no code and touch no real database; if something must be run, run it against a scratch copy. Mark anything the sources do not settle as unsettled instead of guessing. Write the findings to `research/02-store-lifecycle-facts.md`.
