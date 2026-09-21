# The store's lifecycle facts: what a changed or removed claim may do

Type: research
Status: resolved
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

## Answer

Findings, with file and line citations and scratch-store simulations, are in [research/02-store-lifecycle-facts.md](../research/02-store-lifecycle-facts.md) (read-only; the real database was never opened). The facts the later tickets depend on:

- **Who may act.** A `sys:` actor may challenge an admitted claim; `adapter:` and `gen:` are refused. The rule lives only in `hypergraph/actors.py` and its tests, not in the doctrine text or the database.
- **Revoke is not human-only in the store.** `sys:` may also revoke terms, claims and evidence, admit, and close; a claim can be revoked with an empty note. Only three acts are human-only: verifying tier-3 evidence, granting an ambiguity allowance, and voiding a contradicting binding. The map's "only a human makes it final" is therefore **editor policy** and has to be enforced there.
- **Reopen creates a new claim** with a new id, state `PENDING`, `predecessor_ids` and `lineage_hash` set, and no evidence bindings. It works only from a terminal claim (`DENIED`, `REVOKED`, `CLOSED`); a `REVISED` claim is refused. So the revise path is: challenge, begin review, resolve as revise, close, reopen.
- **Atomicity.** A revise is atomic only if the caller wraps every step in one transaction; the library never opens one. A chain split across transactions leaves a legal, withheld state (for example challenged), never a corrupt one. A crash between the candidate-evidence insert and the claim transaction leaves one orphan candidate that a rerun of `load` reuses.
- **The candidate-evidence insert cannot join the hypergraph transaction** from its own connection (it fails with "database is locked" after 5 s). An insert on the same connection works and rolls back with the transaction.
- **Revoking evidence cascades:** its bindings are voided, and an admitted claim becomes challenged. **Revoking a term** challenges every admitted claim that uses it.
- **Terms cannot be revised in the store.** Only revoke and reopen work on terms, so a changed term *label* means a new term.
- **What the loader cannot do today:** it never sees a successor claim (its ids are computed without predecessors, so `verify` reports the closed predecessor as refused on every run); it never inserts a candidate for changed text (so `verify` can never bind new text on an existing claim); it never detects removals; and it never challenges, revokes or reopens anything.
- **Two loader defects found:** `status` can report `claims_not_loaded` as -1 when a claim has drifted, and `verify` can list a claim as both verified and refused when its transaction rolls back.

Nine points are left unsettled by the sources; the ones the tickets must decide are named in [Revise mechanics](03-revise-mechanics.md) and [Removal and revoke](04-removal-and-revoke.md).
