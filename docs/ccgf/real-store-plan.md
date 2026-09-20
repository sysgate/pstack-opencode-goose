# Plan: the real CHI hypergraph store in chi-platform

**Status (2026-09-20): PLAN, and decisions D1 to D4 are made (see the end). No code has been written, nothing in `chi-platform/` has been changed except one appended line in `project-map.md`, and the live ledger was only ever opened read-only. Phase 0 is COMPLETE and Phase 1 slices 1 and 2 (migration + receipt chain; semantic objects, DSN and admission) are BUILT (2026-09-20, see the end); slices 3 onward have not started.**

## What already exists (read on 2026-09-20)

| Fact | Detail |
|---|---|
| The ledger | `infra/chi_agent_gateway/receipts/chi_gateway_ledger.sqlite3`, **433 MB**, WAL mode, `user_version` 0 (no schema versioning, although `AGENTS.md` says to use it) |
| **Not under version control** | `receipts/` is in `.gitignore`. The ledger is a single copy: a bad migration cannot be reverted with git |
| What is in it | 12,129 request receipts, 11,454 response receipts, 49,264 tool decisions, 1,071 candidate-evidence rows, and an empty `ledger_health_checks` table. Requests run 2026-07-03 to 2026-08-15 |
| `candidate_evidence` | Already has `evidence_state` and `admission_receipt_id`. **All 1,071 rows are still `CANDIDATE`; nothing in the code ever admits one.** 1,066 are `model_response` (the doctrine's tier 4) and 5 are `tool_output` (tier 3) |
| Conventions | Per-operation connections with WAL, `busy_timeout` and foreign keys; one module-level lock; `CREATE TABLE IF NOT EXISTS` run by `init_db()` on **every insert**; UUID ids; ISO-text UTC timestamps; `canonical_json` with `ensure_ascii=True` |
| Tests | 87 pass in 0.57 s. `conftest.py` forces every test onto a temporary ledger and asserts it never points at the live one |
| Git | `chi-platform` is a repository on `main`. `AGENTS.md` shows modified (**that is my earlier doctrine edits, uncommitted**) and several `config/` folders are untracked |
| A name clash | The gateway's `admission_state` ADMITTED/DENIED means "the *request* passed policy", not "knowledge was admitted". Its `agent_*_receipts` are request audit records, not CCGF receipts. Both words mean something else in the doctrine |

## What the prototype gives us to port

The prototype (`prototype-hypergraph/`) is throwaway. What carries over is the *logic and the checks*, not the code shape: the nine-state machine, relation signatures, the four boundaries, combination allowances, voiding, lineage, projection, integrity checks, and 87 scenario checks including five sabotage probes. All seven blocking decisions are in the doctrine and match its schema exactly.

## The design

- **Tables** (doctrine §9.1 and §9.3): `semantic_objects`, `hyperedges`, `hyperedge_members`, `evidence_records`, `hyperedge_evidence`, `allowances`, `receipts`. The gateway's own tables are untouched.
- **Clock and ids:** timestamps are the gateway's ISO-text `utc_now()` behind an injectable clock so tests stay deterministic. Ids hash the *source* (decision 3) using the gateway's existing `canonical_json`. Ids will therefore differ from the prototype's; that is expected.
- **Concurrency:** each operation is one connection and one `BEGIN IMMEDIATE` transaction. The receipt chain head is read and appended inside it, so two writers can never fork the chain.
- **Errors:** the prototype's `Refused` becomes a domain error that fails closed. It becomes an HTTP status only if an endpoint is ever added.
- **Evidence:** `candidate_evidence` becomes the evidence lifecycle (see decision D4): model responses map to tier 4, tool outputs to tier 3.
- **Migration:** a versioned, additive, idempotent runner (`PRAGMA user_version`), run **explicitly**, not from `init_db()`, so the live gateway never creates tables by itself and the schema check costs nothing per request.

## Phases

**Phase 0: pre-flight (no code).**
- Back up the 433 MB ledger with SQLite's own backup (not a file copy, since it is a WAL database) to a dated file, and verify it opens and matches row counts.
- Settle git: your uncommitted `AGENTS.md` and untracked configs are yours to commit or set aside, so the new work is a clean diff on its own branch. I will not commit anything unless you ask.
- *Done when:* a verified backup exists and the working tree state is agreed.

**Phase 1: schema, store library and tests. Not wired into the gateway.**
- A subpackage split by concern (schema and migration, hashing and ids, receipts and chain, objects, evidence, hyperedges and boundaries, allowances, revision, projection, integrity). About 1,000 to 1,400 lines plus a similar amount of tests.
- Port every prototype scenario as pytest, the integrity attacks, and the sabotage probes as tests that must fail when the rule is removed.
- *Done when:* all ported checks pass; the existing 87 tests still pass; the migration run against a **copy** of the live ledger adds the new tables and leaves every existing table's row count and checksum unchanged; running it twice changes nothing.
- *Rollback:* drop the new tables, or restore the backup.

**Phase 2: gateway integration.**
- Promotion of candidate evidence into admitted evidence in one transaction with its receipt.
- An integrity command beside `verify_sqlite_ledger.sh`, and a startup health check.
- The chain-head anchor (decision D3).
- *Done when:* the end-to-end harness still passes and the integrity command reports clean on the live ledger.

**Phase 3: the glossary and evidence lifecycle.**
- Port the glossary loader and query tool to the real store, so the CHI glossary you asked for lives in the authority store, not a prototype file.
- Only if D4 is yes: 1,071 existing candidate-evidence rows keep their state and gain a path to admission, including recording a human verification (F19).

**Phase 4, later and only if wanted:** a read-only MCP or HTTP query surface and a real projection renderer. Not planned in detail.

## Risks and what I will not do

- **The single 433 MB ledger:** mitigated by the verified backup, additive-only DDL, explicit migration, and trying it on a copy first.
- **Write contention:** hypergraph writes are rare next to request logging, and transactions are short with a 5 s busy timeout. If it ever bites, the chain is the place it would show (D3).
- **Hash incompatibility:** ids and hashes will not match the prototype's; nothing depends on them.
- **Name clash:** I will document "request admission" versus "knowledge admission" and will not rename live columns.
- **Without asking I will not:** touch an existing table, run a migration on the live ledger, change the gateway's request path, commit, or edit the doctrine.

## Decisions for you (recommendation first)

**D1. One SQLite file or two?** Recommend the **same file, additive tables only.** In WAL mode SQLite gives no atomicity across two files, and promoting evidence must update `candidate_evidence` and write its receipt together. Foreign keys then also hold. The cost is that new code shares a file with 433 MB of audit data, which the backup, additive-only DDL and copy-first testing are there to cover. *Alternative:* a separate `chi_hypergraph.sqlite3`, safer for the audit data, but evidence promotion could then half-complete.

**D2. Where does the code live?** Recommend a **subpackage of the gateway** (`app/hypergraph/`), reusing its settings, hashing and the test-isolation fixture. *Alternative:* a separate installable package, cleaner boundaries but it duplicates the config and the isolation guard.

**D3. Receipt chain and anchor?** Recommend **one global chain, and after each append write the chain head to a sidecar JSONL file outside the database.** It is cheap, and it catches anyone who rewrites only the database. It does not stop someone who can rewrite both files; that limit stays as the doctrine states it. *Alternatives:* a chain per subject (parallel writes, but each needs its own anchor), or no anchor yet.

**D4. Evidence lifecycle?** Recommend **use `candidate_evidence` as the lifecycle**: states `CANDIDATE`, `ADMITTED`, `DENIED`, `REVOKED`, linked to the admission receipt, with an admitted, content-addressed `evidence_records` row behind it. This resolves F8 and F19 (a human verification becomes a receipt). It needs a doctrine amendment, since the doctrine's `EvidenceRecord` has no lifecycle. *Alternative:* keep evidence as the doctrine has it today, simpler, with F8 and F19 left open.

## Decisions made (2026-09-20)

All four recommended options were chosen.
- **D1:** the same SQLite file, additive tables only.
- **D2:** a subpackage of the gateway, `app/hypergraph/`.
- **D3:** one global receipt chain, with the chain head written to a sidecar JSONL file outside the database after each append.
- **D4:** `candidate_evidence` becomes the evidence lifecycle (`CANDIDATE`, `ADMITTED`, `DENIED`, `REVOKED`), with an admitted content-addressed `evidence_records` row behind it.

**Consequences to carry into the work**
- **D4 needs a doctrine amendment** (the doctrine's `EvidenceRecord` has no lifecycle). It is **not applied**; the doctrine sync is stopped. It also touches F8 (the allowance rule "lapses when the evidence is revised or revoked" becomes evaluable) and F19.
- **D3's anchor is now specified** enough to build: the sidecar JSONL is the outside-the-database copy of the chain head. The doctrine still says the anchor is unspecified, so that wording will need to catch up.
- **D1 raises the stakes of Phase 0.** The ledger is 433 MB, not under git, and shared with live audit data; nothing else in the plan is safe without the verified backup first.

## Phase 0 result (2026-09-20)

- **Backup:** `chi-platform/infra/chi_agent_gateway/receipts/backups/chi_gateway_ledger.pre-hypergraph-20260920.sqlite3` (454 MB, mode 400, folder mode 700) with a manifest beside it. Made with SQLite's backup API from a read-only connection while the gateway was not running. It is in a gitignored folder, so it cannot be committed by accident. It shares the disk with the live ledger, so it protects against a bad migration, not a disk failure.
- **Verified:** `integrity_check` is `ok`; per-table row counts and a SHA-256 over every row match the live ledger (12,129 / 11,454 / 1,071 / 0 / 49,264), as does the schema; the live ledger was fingerprinted again afterwards and is unchanged. The check was proved capable of failing: altering one field of one row in a scratch copy changed exactly that table's fingerprint. A write attempt on the backup is refused.
- **Git:** on `hypergraph-store`, branched from `main` at `1ccf41c`, after two commits of my own files (`da1b4b0` the doctrine sync in `AGENTS.md`, `1ccf41c` the `project-map.md` log note). The seven untracked `*.env.example` files are not mine and were left alone.
- **Baseline:** 87 existing tests pass on the new branch.
- **Deviation:** I did not append a Phase 0 line to `chi-platform/project-map.md` (its folder rule), to keep the branch point clean. It goes in with the first Phase 1 commit.

## Phase 1, slice 1: migration runner and receipt chain (2026-09-20)

Built in `chi-platform/infra/chi_agent_gateway/app/hypergraph/` on branch `hypergraph-store`: `migrations.py`, `receipts.py`, `db.py`, `clock.py`, `hashing.py`, `errors.py`, plus `tests/test_hypergraph_migrations.py` and `tests/test_hypergraph_receipts.py`. `pyproject.toml` now lists `app.hypergraph` (it listed only `app`, so a normal install would have silently left the subpackage out).

- **Migrations:** versioned with a checksum per migration in `hypergraph_migrations`; additive-only (plain `CREATE TABLE/INDEX/TRIGGER`, no `IF NOT EXISTS`, gateway tables may appear only in a `REFERENCES` clause); one `BEGIN IMMEDIATE` for the whole run; an edited migration or a database newer than the code is refused; run explicitly, never from `init_db()`.
- **Receipts:** one global chain. The database itself refuses updates, deletes, a skipped `seq` and a wrong predecessor (triggers), and a foreign key adds a second guard against removing a middle receipt. `verify_chain()` recomputes every id.
- **Tests:** 32 new (119 with the existing 87). Eleven sabotage probes were run, each disabling exactly one rule, and each was caught by the test for that rule; two early probes were crude (they broke everything, not the one rule) and were redone precisely. The probes exposed one missing test (that `migrate()` itself refuses a non-additive migration), now added.
- **Trial on a copy of the real data:** the migration applied to a copy of the verified 454 MB backup left all five gateway tables identical (rows, content hash, schema text, indexes), was idempotent, and left a verifying chain. The live ledger and the backup were untouched.

**Deviations and limits to carry forward**
- The doctrine's `Receipt` lists both `id` and `hash`; the store has only `id`, which *is* the hash. The doctrine wording should say so.
- A chain cannot detect **truncation** (removing the newest receipts). Only the anchor (D3, Phase 2) can.
- Nothing has been run against the live ledger.

**Coordination incident.** A second Claude session (`chi-8c`, idle, started 9 hours earlier) works in this same repository. While I built slice 1 it committed the seven `*.env.example` files (`afb37d5`) and then my slice-1 files (`dfc6807`, written up as "118 passed", which was true at that moment). I made neither commit. Content is intact, and my only uncommitted change is one added test. Two sessions sharing one working tree and one branch can overwrite or commit each other's work.

## Coordination resolved, and one thing you should know about GitHub

The peer session `chi-8c` agreed in writing to stay off `hypergraph-store`, `app/hypergraph/` and `tests/test_hypergraph_*.py`, listed everything it had done, and will use a separate worktree or branch and ask its own user first. It made three commits at its user's explicit request (`afb37d5` the `*.env.example` templates, `dfc6807` my slice-1 files, `8cfeabd` a `.gitignore` update) **and pushed `main` and `hypergraph-store` to the private GitHub repository `sysgate/CHI`**, so slice 1 is on a remote. I did not push anything. I scanned every commit in the pushed history for credential-shaped strings (API-key, cloud, GitHub, Slack, Google, private-key and JWT patterns): none, and no secret or database file was ever tracked. My uncommitted work (slice 2) is not on the remote. Amending or rebasing `dfc6807` or `8cfeabd` would now need a force-push, so I will not.

## Phase 1, slice 2: semantic objects, DSN narrowing, semantic admission (2026-09-20)

Built on `hypergraph-store` (uncommitted): migration 2 (`semantic_objects`), `objects.py`, `states.py`, `actors.py`, `tests/test_hypergraph_objects.py`. Suite: **178 passed** (87 existing, 91 hypergraph).

**The doctrine's rules now live in the database, not only in Python.** Triggers refuse: an object inserted in any state but CANDIDATE or with a DSN state (no planted admitted row); any deletion; any change to id, source text, scope, context, predecessors, lineage or creation time; any transition not in the section-7 table (so terminal states cannot be resumed even by raw SQL); and a move to ADMITTED without a `SEMANTIC_ADMIT` receipt (decision 7). A test proves the Python state machine equals the frozen trigger table.

**Verification.** Eleven sabotage probes, each disabling exactly one rule (five database rules, six Python rules), each caught by the test for that rule. Trial on a scratch copy of the verified backup: migrations 1 and 2 applied, the five gateway tables identical in row content, hash, schema and indexes, an object flow and the delete-refusal worked, the chain verified, the live ledger untouched.

**Findings from building it**
- **The proposing actor is recorded nowhere.** There is no receipt type for a proposal, and the prototype's `actor` argument on a proposal was never stored. Who proposed a candidate is lost; only who narrowed and who admitted it is on the trail. Recommend a `proposed_by` field or a proposal receipt.
- **The admission trigger checks that a `SEMANTIC_ADMIT` receipt exists for the subject, not that it is the right one.** Someone with governance access could append one and then update the row. That is inside the governance trust boundary, but it is a limit.
- **Object review has no resolution (F12 still open):** the transition table lets an object reach `UNDER_REVIEW` (a DSN conflict does), but nothing resolves it, and the `UNDER_REVIEW -> ADMITTED` edge has no receipt requirement for objects.
- **Two hooks are deliberately absent until hyperedges exist:** narrowing an admitted bounded term should revalidate the allowance-bound bindings that use it, and revoking an object should challenge the hyperedges that use it.

## D4 refined (2026-09-20)

D4 ("use `candidate_evidence` as the evidence lifecycle") is specified in `proposed-evidence-lifecycle.md`, with decisions E1 (tier 4 is never bindable), E2 (refusal-only triggers on the gateway table, a narrow exception to additive-only) and E3 (only a human verifies tier 3). The doctrine text was applied on 2026-09-20; slice 3 (evidence) builds against it.

