# Plan: the real CHI hypergraph store in chi-platform

**Status (2026-09-20): PLAN, and decisions D1 to D4 are made (see the end). No code has been written, nothing in `chi-platform/` has been changed except one appended line in `project-map.md`, and the live ledger was only ever opened read-only. Phase 0 is COMPLETE and Phase 1 (schema, store library and tests) is COMPLETE as of 2026-09-20: migration + receipt chain, semantic objects and DSN, the migration guard and evidence, hyperedges, bindings, allowances, the four boundaries, admission, review, the cascades, projection and the integrity check (see the end). Phase 3 (the glossary loader, verifier and query tool) is BUILT and proven on a scratch copy of the real ledger, but has NOT been run on the live ledger. Phase 2 (the chain-head anchor, the startup health check, the verifier script) is BUILT and proven on a scratch copy, and NOT yet run on the live ledger.**

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

## Phase 1, slice 3: the migration guard and evidence (2026-09-20)

Built on `hypergraph-store` (uncommitted): a stricter guard in `migrations.py`, migration 3 (`evidence_records` and the refusal-only triggers on `candidate_evidence`), `evidence.py`, `tests/test_hypergraph_evidence.py`. Suite: **252 passed** (87 existing, 165 hypergraph).

**The guard first, as recommended.** Every trigger in every migration must now be `BEFORE`, contain nothing but `RAISE(ABORT, ...)`, and hold no comments. The one exception to "never touch a gateway table" is such a trigger on `candidate_evidence`, on `UPDATE` or `DELETE` only (never `INSERT`, so the gateway can never be blocked from inserting), named `hypergraph_*` so it can be identified and dropped. A migration that needs a gateway table refuses atomically if it is missing.

**Evidence.** `candidate_evidence` is the lifecycle (E-decisions applied): only a human verifies tier 3; generative evidence is never admitted; the stored hash is re-verified against the body and sealed in the admission receipt; denial and revocation need their receipts; the body, hash, kind, source and provenance of a candidate never change; candidates are never deleted. All of it is enforced by triggers in the database, not only in Python. `evidence_records` cannot even hold tier 4 (a CHECK), so a generative candidate cannot become a binding target.

**Verification.** 35 sabotage probes in three rounds: 11 on the guard (one real gap found and fixed), 24 on the evidence rules (one gap found and fixed). Each probe disables exactly one rule and each is caught by the test for that rule. Trial on a scratch copy of the verified backup: migrations 1 to 3 applied; the five gateway tables identical in definition and content; **all 1,071 real candidate hashes verify against their bodies**; a real tool output was admitted by a human, and a real model response, non-human verification, a body edit, a delete and a resurrection were all refused; the gateway's own insert path still works; only that one candidate's lifecycle columns changed; the live ledger was untouched.

**What building it taught us**
- **A real hole in my own first guard.** A quote mark inside a comment makes a scanner that strips string literals mistake code for a string, so a disguised `UPDATE` slipped through and SQLite really executed it. Found by a sabotage probe that was *not* caught; fixed by banning comments in triggers, with the attack itself as a test and a second test proving the attack is real.
- **Two rounds of my probes were crude.** A probe that breaks the whole migration proves nothing about the rule under test, and my `SELECT 1` no-ops were rejected by the new guard. Redone with a no-op the guard accepts.
- **A rule that another trigger also enforces is untested.** The candidate-skip transition was protected twice, so the transition table alone was never exercised until a test supplied the receipt that satisfied the other trigger. Some paths (`ADMITTED -> DENIED`) are refused twice by structure and cannot be isolated at all.
- **SQLite does not define which of several refusing triggers fires first**, so tests assert that an update is refused and accept either message.

**Limits to carry forward**
- **The database cannot stop someone inserting an `ADMITTED` candidate row directly**, because triggers on `INSERT` for a gateway table are banned (they could block the gateway). The integrity check (slice 8) must detect an admitted candidate with no evidence record and receipt.
- **The revocation cascade to bindings is not built yet**; it arrives with bindings (slice 4).
- **A doctrine wording mismatch:** the doctrine's timestamps are "epoch numbers", but the gateway and this store use ISO-8601 text.

## Phase 1, slice 4a: hyperedge candidates and members (2026-09-20)

Slices 1 to 3 are committed on `hypergraph-store` in five scoped commits (`6035f51` to `7781f6e`, not pushed). Slice 4a is built and **not committed**: migration 4 (`hyperedges`, `hyperedge_members`, 22 triggers), `relations.py`, `hyperedges.py` (propose, get, members_of, move, reopen), `tests/test_hypergraph_hyperedges.py` (193 tests). Suite: **445 passed**.

**Why 4a stops short of admission.** The 據界 boundary needs evidence bindings, and admitting a hyperedge with a stand-in for it would be exactly the optimistic default the doctrine forbids. So 4a builds what can be built and verified honestly on its own: the candidate, its members, the signatures and the state machine, all enforced by the database. Bindings, allowances, voiding, the four boundaries, admission and the cascades are **slice 4b**.

**What the database now enforces for hyperedges**
- Born a `CANDIDATE` with no receipt; never deleted; identity and source never change; the admission receipt is set once and only with the move to `ADMITTED`.
- The frozen state machine, and a **relation signature** checked when the candidate leaves `CANDIDATE` (every member role allowed for the type, every required role present). Python and the database are driven with every relation type and role combination and must agree.
- Members are added only while the hyperedge is a `CANDIDATE`, only if they are admitted semantic objects, and never change or go away.
- **Every move needs its receipt: of the right kind, the latest on the hyperedge, and naming the move** (`from` and `to` in its basis).

**What building it taught us**
- **A stale receipt could have authorised a new move.** My first rule was "the latest receipt on the hyperedge is of the right kind". The tests showed that after a move the receipt that justified it is still the latest, so `CHALLENGED -> UNDER_REVIEW` passed on the same `REVISION_OPEN` that justified the challenge, and `REVISED -> CLOSED` on the receipt for `REVISED`. Fixed by making each move receipt name its move, checked in the database. Returning from review to `PENDING` now needs its own receipt (`REVISION_CLOSE`, `PEND`); the doctrine did not say it needed one.
- **A NULL slips through a `NOT IN`.** A hyperedge with no receipt gave a NULL comparison, and `RAISE ... WHERE NULL` does not fire. The rule now coalesces, and a test covers a hyperedge with no receipt at all.
- **45 sabotage probes, one gap found.** Each disables one rule. The closed relation-type list was not caught until a test drove a raw insert of an unknown type. All 45 are now caught (the baseline passes).
- **Two of my own tests had a false premise** (two triggers refuse the same move and SQLite does not define which fires first; a `BEFORE INSERT` trigger fires before a `CHECK`). Fixed by supplying the receipt that satisfies the other rule so each test isolates one rule, and by dropping the one case that cannot be isolated.

**Trial on a scratch copy of the verified backup:** migrations 1 to 4 applied; the five gateway tables identical in rows, content and schema; the only change on them is the seven `hypergraph_` triggers from slice 3; a hyperedge over two real-shaped objects was created; admission without a receipt, deletion, a source edit, a late member and a planted `ADMITTED` row were all refused by the database; all 1,071 candidates still `CANDIDATE`; chain and `quick_check` ok; second run applies nothing; the live ledger was untouched (454,098,944 bytes).

**Open for 4b (decisions I will take, and flag)**
- A `CAUSAL` hyperedge with two `SUBJECT` members: the doctrine does not say. The prototype's cycle check assumed one subject and one object. Recommend the 徑界 check treat each subject as a cause of each object.
- Admission by boundaries must write the `from`/`to` in each move receipt, and the objects module still needs its cascade hooks (revoke, narrowing) now that hyperedges exist.

## Phase 1, slice 4b: bindings, allowances, boundaries, admission, review, cascades (2026-09-20)

Slices 1 to 4a are committed (`6035f51` to `a0e178d`). **Slice 4b is built and NOT committed**: migrations 5 (`bindings`: `allowances`, `hyperedge_evidence`) and 6 (`boundaries`), `bindings.py`, `revision.py`, `boundaries.py`, `admission.py`, cascades in `objects.py` and `evidence.py`, `tests/hg_helpers.py`, `tests/test_hypergraph_bindings.py` (98) and `tests/test_hypergraph_admission.py` (62). Suite: **604 passed** (87 gateway + 517 hypergraph).

**What the database now enforces (in addition to slices 1 to 4a)**
- A binding is born un-voided, only on a PENDING or ADMITTED hyperedge, only for **admitted, unrevoked** evidence (so generative evidence can never be bound: decision E1 is structural), with its own `EVIDENCE_ADMIT` receipt as the latest on the hyperedge, naming the evidence and polarity.
- A bounded ambiguous member needs an allowance for **this** binding, covering every bounded member, granted by a human who is not the binding's proposer. An allowance is where nothing is bounded is refused.
- A binding is never deleted and never restored; voiding is once, with its own `REVISION_CLOSE` receipt naming the evidence, and dismissing a contradiction needs a human receipt.
- **Admission and reaffirmation clear the boundaries in the database**: every member admitted, supporting evidence that still counts, no contradiction that still counts, a confidence bound. A confidence bound is itself a receipt, and the envelope is frozen once a hyperedge leaves PENDING. Only 徑界 (no causal loop) stays in Python, because a trigger cannot walk a graph.

**Cascades (修界)**
- Revoking evidence voids every binding that uses it; a hyperedge left without support becomes CHALLENGED if it was ADMITTED, and records UNSUPPORTED if it was PENDING. This makes the allowance rule "lapses when the evidence is revoked" (F8) evaluable.
- Revoking a member lapses allowances that covered it and challenges every ADMITTED hyperedge that uses it. Narrowing an admitted bounded term revalidates its hyperedges.

**What building it taught us**
- **A contradiction must not vanish when an allowance lapses.** My first `support()` filtered every allowance-bound binding by its allowance, so a lapsed allowance made a contradiction stop counting without a human dismissing it: fail-open. Now only *supporting* bindings depend on their allowance; a contradiction counts until a human dismisses it, or until its evidence is revoked (revoked evidence asserts nothing).
- **Voiding a contradiction needs a human, and a machine revokes evidence.** The two rules collide in the revocation cascade. Resolution: a non-human revocation leaves a contradicting binding un-voided (it stops counting anyway); a human revocation voids it. **The doctrine says "revoking evidence voids every binding that uses it"; this is a narrower rule and needs to be stated there.**
- **`proposed_by` is not in the doctrine's binding schema**, but the database cannot otherwise refuse an allowance granted by the proposer. It is stored on the binding.
- **A hyperedge that leaves PENDING by database rules needs readiness.** Once the database checked the boundaries, 96 older tests that raw-admitted a bare hyperedge failed, correctly. Fixed with a shared `ready()` helper rather than by loosening any rule.
- **Two rules cannot be isolated by a test.** Only-SUPPORTS-counts-as-support in the admission trigger is redundant with the contradiction trigger (a hyperedge with only a contradiction cannot be admitted either way); several `CHECK`s sit behind triggers that fire first. Left as defence in depth and noted in the tests.

**Verification.** 67 probes on bindings, allowances and revision (one gap found: the closed polarity list) and 50 on the boundaries, admission, review resolution and cascades (three not caught at first: two real gaps closed with tests, one redundant rule documented). Every rule now has a test that fails when it is removed. Trial on a scratch copy of the verified backup, with a REAL tool-output candidate: verified by a human, bound, admitted through the boundaries, challenged by a contradiction, not reaffirmable while contradicted, not dismissable by a machine, dismissed by a human and reaffirmed, then revoked, which voided the binding and challenged the hyperedge. All 1,071 candidates' immutable columns unchanged, the four other gateway tables identical, chain and `quick_check` ok, live ledger untouched.

**Decisions taken in this slice that the doctrine does not state (please confirm or overrule)**
1. Returning from review to PENDING (`rerun`) needs its own `REVISION_CLOSE` `PEND` receipt.
2. A `CAUSAL` hyperedge with several SUBJECT members: each subject is a cause of each object when checking for loops.
3. Evidence cannot be bound while a hyperedge is UNDER_REVIEW or CHALLENGED, only while PENDING or ADMITTED. Evidence that arrives during a review has to wait for the outcome. That is inherited from the prototype and may be too strict.
4. A voided binding is never re-bound; a retry needs a new hyperedge that names the old one (F7).
5. The doctrine's timestamps are still "epoch numbers" while the store uses ISO text.

**Still open**: the database cannot block a planted ADMITTED candidate row in `candidate_evidence` (INSERT triggers on gateway tables are banned); 徑界 has no temporal-overlap check (section 8.4 point 2); nothing anchors the chain head outside the database (D3).

## Phase 1, slices 5 and 6: projection and the integrity check (2026-09-20)

Slices 1 to 4b are committed (`6035f51` to `745bfc8`; 1 to 4a are also on the private remote via the other session's push). **Slices 5 and 6 are built and NOT committed**: `integrity.py` (the check and a read-only command), `projection.py`, `tests/test_hypergraph_integrity.py` (72). Suite: **676 passed** (87 gateway + 589 hypergraph).

**The integrity check** answers what neither triggers nor the chain can: is every row still explained by the record? It is read-only and fail-closed. Its checks: guards (every table, index and trigger the migrations created is present and unaltered, and no unknown trigger sits on our tables or the gateway's candidate table); the receipt chain; candidates (body still matches its hash; an ADMITTED, DENIED or REVOKED one is backed by a record and receipts; a generative one is never admitted); evidence records (hash sealed in the receipt, text canonical, tier 3 verified by a human); semantic objects; hyperedges (signature, admission receipt, state explained by the latest move receipt, and an ADMITTED one **still clears every boundary**, including no causal loop); bindings and allowances; orphan receipts. The command is `python -m app.hypergraph.integrity [--db PATH]`, opened read-only, exit 0 clean and 1 not.

**It closes the known limit from slice 3**: the database cannot stop someone inserting an `ADMITTED` candidate row into the gateway's table (INSERT triggers there are banned). The check finds it (`ADMITTED_CANDIDATE_WITHOUT_RECORD`), and reproduced on a copy of the real ledger with the gateway's own insert path. It also finds what the triggers cannot: a dropped or weakened trigger, an added column, a trigger someone planted, a forged evidence hash with recomputed text (the prototype's F17 attack), a hyperedge admitted behind the boundaries, a causal loop, a contradiction dismissed by a machine, an allowance granted by its proposer.

**Projection** is a derived view recomputed on every call, and it fails closed: only an ADMITTED hyperedge that clears the integrity check is assertable. A problem about a hyperedge withdraws that hyperedge; a global problem (a broken chain, a missing guard) withdraws everything. A problem about an unrelated candidate withdraws nothing.

**What building it taught us**
- **The check has to tolerate being run on a store it does not understand.** Run on the unmigrated real ledger, it first reported a wall of "guard missing" for guards that were never created. It now compares only the migrations that have run, and says one thing: migrations pending.
- **Tests that tamper need the guards intact.** The tamper helper drops every trigger, tampers, then restores them exactly, so the only difference from a clean store is the tamper. That is why each check has a test that fails when it is silenced.
- **A weakness in my own probes**: the probe for "the command opens read-only" survived because an unchanged file hash proves nothing; a test now captures the connection URI.

**Verification.** 54 probes (one silencing each problem code, plus compound conditions and the projection), one gap found and closed. Trial on a scratch copy of the verified backup with real data: the unmigrated ledger reports only `MIGRATIONS_PENDING`; after a real admission flow (a real tool-output candidate verified by a human) the check is clean (0.01 s for 1,071 candidates); a planted `ADMITTED` candidate row is the only problem reported and does not withdraw the unrelated hyperedge; the command exits 1; live ledger untouched.

**Limits that remain**
- Chain truncation (deleting the newest receipts and their effects) is undetectable inside the database. Only the chain-head anchor outside it (decision D3, Phase 2) can catch it.
- Someone who can rewrite the whole database and rebuild the chain is out of scope, as the doctrine states.
- Lineage hashes are not recomputed (a later receipt on a terminal predecessor would make a false alarm); the predecessor's existence and terminal state are checked.
- 徑界 has no temporal-overlap check (section 8.4 point 2).

## Phase 3: the CHI glossary in the real store (2026-09-20)

Built and **not committed**: `app/hypergraph/glossary.py` (parse, plan, `load`, `verify`, `status`, `define`, and the command `python -m app.hypergraph.glossary`) and `tests/test_hypergraph_glossary.py` (51). Suite: **725 passed**. The migrations and the loader have never been run on the live ledger.

**Two phases, because the doctrine leaves no other honest design.** `load` is the machine phase: it narrows each term on its recorded basis (the source), has the adjudicator admit the objects, proposes every claim as a `PENDING` hyperedge with confidence 1.0 ("the source states this", not "this is correct"), and inserts each piece of evidence as a `CANDIDATE` through the gateway's own insert path. It admits nothing about evidence. `verify` is the only step that admits evidence, and tier-3 evidence can only be verified by a human, so the command needs `--by human:NAME` and a note, and refuses anything else. **The loader never supplies a human on anyone's behalf, and I did not run it as one.** In the trial the identity is `human:trial-verifier`, on a scratch copy, marked as such.

**Safety properties (each has a test that fails when it is removed).** It refuses the configured live ledger without an explicit `--allow-live`, refuses an unmigrated store (migrations stay an explicit step), and refuses a plan whose collisions the map no longer states. It is idempotent (deterministic ids: a second load and verify add no receipts) and resumable after an interruption. If a source changed after it was loaded, the claim is reported as **drift** and left alone, not silently re-pointed: revoking and reloading it is a human decision. `define` reads only claims that are admitted and pass the integrity check, and fails closed.

**Real result (scratch copy of the verified backup, real glossaries):** 75 terms, 139 avoided aliases (7 with a qualifying note), 3 groups, 227 objects, 264 claims. Load 0.4 s, verify 0.2 s. After load: integrity clean, no evidence admitted. After verification by the trial identity: 264 hyperedges ADMITTED, 264 evidence records, 1,510 receipts, integrity clean, chain verifies, 1.9 MB added. The five gateway tables are unchanged except two insert-only additions: 3 request receipts in `agent_request_receipts` and 264 new candidate rows (all now ADMITTED); the 1,071 original candidates are all still `CANDIDATE` with their immutable columns unchanged. The live ledger was untouched.

**What building it taught us**
- **Gateway rows the loader must write have a meaning it does not own.** Evidence candidates need a request receipt, and a receipt's `admission_state` means "the request passed policy". The loader records `NOT_EVALUATED`, because the gateway never evaluated anything for it. The rows still sit in the gateway's audit tables; on the live ledger that is a real, insert-only write, so it needs your explicit go-ahead.
- **Evidence provenance points at the ledger request, not the file.** The evidence record's `provenance_uri` is `gateway-ledger://request/<id>`; the file, its hash and the anchor are in the request body and the candidate body. Fine for audit, but the doctrine's "immutable path or locator" is satisfied only indirectly.
- **A new evidence kind would need a new trigger, which the additive guard forbids.** Glossary extractions are recorded as `tool_output` from an adapter (`glossary-md`), tier 3, because a `document` kind cannot be admitted without dropping the slice-3 kind trigger. Noted as a limitation, not hidden.
- **`define` had no ORDER BY**: which supporting binding gave the definition was arbitrary. Found only because a probe survived; it now takes the earliest counting binding.
- **Probes.** 40 on the loader and `define`; six gaps found and closed with tests (an alias and a term sharing text in one glossary, resuming a verification, a request following file content, voided bindings never supplying a definition, and others).

**Still open before this can run on the live ledger:** (1) your explicit go-ahead to run the six migrations there (a one-way step on a single 454 MB file, backed up at `receipts/backups/`); (2) a real human to run `verify --by human:<you>`; (3) Phase 2 (the chain-head anchor and a startup health check), so tampering with the newest receipts is detectable.

## The CHI glossary prototype database exists (2026-09-20)

Your objective: the CHI Platform glossary in the hypergraph database, to begin prototyping the CHI application. Decisions you made: a **separate prototype database** (not the live gateway ledger), and **you run verification yourself**.

**Done.** `~/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3` (1.1 MB, mode 600, gitignored, rebuildable) was created with the gateway's own schema plus the six hypergraph migrations, and the machine phase of the loader was run on your real glossaries: 75 terms, 139 avoid entries (136 distinct words), 227 objects, 264 claims. Integrity is clean. The live ledger was not touched (size and mtime unchanged). `hypergraph-db/README.md` documents the model, the commands, a read-only Python usage example (checked against the real file) and how to rebuild.

**Not done, by design: verification.** Every claim is `PENDING` and every piece of evidence a `CANDIDATE`, so nothing is *asserted* yet and `define` says "(not verified yet)". Under the doctrine only a human admits tier-3 evidence, and I did not record a verification on your behalf. The exact command, with `--by human:YOURNAME`, is in the README.

**Built along the way:** `python -m app.hypergraph.migrations {status|migrate} --db PATH [--create]` (creates a new store with the gateway schema; refuses the live ledger and existing files; `status` is read-only) and a scoped `db.pointed_at()` that redirects the gateway ledger setting for one command and restores it. **A real hazard was found and fixed**: the first version of the command left the redirection in place, so a later command in the same process treated its target as the configured ledger. 8 probes on the new command; one gap (read-only `status`) closed with a test. Suite: 733 passed.

## Phase 2: the chain-head anchor, the startup health check and the verifier (2026-09-20)

Built and **not committed**: `app/hypergraph/anchor.py`, `app/hypergraph/health.py`, a hook in `db.write_transaction`, `integrity.py`/`projection.py` reading the anchor, `scripts/verify_hypergraph_integrity.sh`, and 65 tests across `test_hypergraph_anchor.py`, `_health.py`, `_verify_script.py`. Suite: **798 passed**. The live ledger was never opened.

**The anchor (decision D3).** After every committed write, `write_transaction` appends the receipt chain's head (sequence number and id) to a sidecar JSONL file beside the database (`<db>.anchor.jsonl`, mode 600; `CHI_HYPERGRAPH_ANCHOR_PATH` overrides, `CHI_HYPERGRAPH_ANCHOR=off` disables). Each line is hashed with the line before it, so editing or deleting a line in the middle of the file is detected. The integrity check then verifies that the database chain still contains every anchored head, which catches what the chain alone cannot: **someone who changes a receipt and rebuilds every id after it leaves a chain that verifies on its own, but no longer matches the anchor** (proved on a copy of the real ledger). A truncated chain is shorter than the newest anchored sequence number. `python -m app.hypergraph.anchor {status|sync}`: `sync` writes the first anchor or catches up a lag, and **refuses to bless a chain, or an existing anchor, that does not verify**. A write failure is logged and counted, never raised (the transaction has already committed); the anchor then merely lags, which the check reports as a warning.

**The startup health check.** `app/hypergraph/health.py` runs at gateway startup (`lifespan`) and feeds the existing `/healthz`. It is read-only, opens the ledger `mode=ro`, never raises into the gateway and never touches the request path. If the ledger has no hypergraph store it reports `present: false` and changes nothing, so today's live gateway behaves exactly as before. If the store fails its check, `/healthz` is `degraded` and the gateway keeps answering and auditing: **it reports, it does not stop**, because the gateway's own audit ledger must keep working. The result is cached for 60 seconds.

**The verifier.** `scripts/verify_hypergraph_integrity.sh` sits beside `verify_sqlite_ledger.sh`: it runs the integrity check and the anchor check read-only. It exits 0 clean **or when the ledger has no store (SKIP)**, 1 on a problem, 2 if it cannot run.

**Real result (scratch copy of the verified backup, real glossaries).** The script skipped the unmigrated copy. After load and trial verification: 755 anchor lines (223 KB), chain and anchor agree, script passes, `/healthz` ok with the store present and clean. **Attack 1** (rewrite a receipt, rebuild the whole chain): the chain verified on its own; integrity reported `ANCHOR_MISMATCH`, the script failed, `sync` refused to bless it, `/healthz` went `degraded` while the gateway kept answering. **Attack 2** (delete the newest 25 receipts): `ANCHOR_CHAIN_TRUNCATED`. Deleting a line from the middle of the anchor file: `ANCHOR_FILE_TAMPERED`. Load time with anchoring on: 0.5 s (was 0.4 s). Live ledger unchanged.

**What building it taught us**
- **The check's own test data had to be honest.** My first health tests reported a "clean" store as unhealthy: the receipts named subjects that did not exist, and the integrity check correctly called them orphans.
- **Two rules turned out redundant**, and are noted rather than tested: the projection's `ANCHOR_` prefix (an anchor problem already has no subject, so it is already global) and a cache eviction in `startup` (`cache_seconds=0` already forces a fresh check; the dead line was removed).
- **Probes.** 46 across Phase 2; four real gaps closed with tests (an anchored receipt deleted on its own, the health check opening read-only, and two more); the read-only-open probe recurred for the third time, a pattern worth a shared test helper.

**Limits that remain.**
- **Someone who can rewrite BOTH the database and the sidecar is not stopped**, as the doctrine states. The sidecar is on the same machine. Keep a copy elsewhere, or make it append-only at the filesystem level, to raise the bar.
- **Truncating the tail of the sidecar is not detectable**, and shows only as lag (there is a test that says so).
- **The anchor lags if a write cannot be anchored**, until `anchor sync` (which refuses to bless a problem).
- **Gateway integration is deliberately minimal.** There are no new HTTP endpoints and nothing on the request path (that is Phase 4, only if wanted).

**Not done, and needs your decision.** Running the six migrations on the live ledger, then the glossary load, then your verification. With Phase 2 in place, tampering with the newest receipts is now detectable, which was my stated precondition for that step.

## First application primitive: `lint` (2026-09-20)

At your "go with your recommendations" I picked the first query to build on the store: **check text against the glossary**. `python -m app.hypergraph.glossary lint --db DB --text "..."` (or `--file F`, `-` for stdin) flags words the glossary says to avoid, names the term to use instead (with any qualifying note, so the advice can be conditional), and flags words that mean different things in different contexts (the gate's *Scope* is not CCGF's). Whole words and phrases, case-insensitive, longest phrase first; exit 1 if anything is flagged. It is read-only (`mode=ro`) and uses **only claims that are admitted and pass the integrity check**: before verification it reports nothing and says why, and it never reports a claim that is only pending. Built and **not committed**: `lint`/`vocabulary` in `glossary.py`, 15 tests (suite 814 passed), 15 probes, one real gap closed (a collision looked up from its other side).

**On your real glossary** (a throwaway copy, verified under the marked identity `human:trial-verifier`, then deleted; the prototype database was untouched): it flagged `approval` (use Admission or Verification), `sign-off` (Verification), `workspace` (Scope) and marked `scope` and `audit log` as ambiguous across the two contexts. It also flagged `scope` as an avoided word in favour of *Covered tool*, with the note "that names a folder tree": that is the gate glossary's own deliberate disambiguation, kept as a condition.

## Wiring lint into an agent workflow: the glossary hook (2026-09-20)

You chose to wire `lint` into an agent workflow. The workflow that exists here is Claude Code, so it is a **PostToolUse hook** (`app/hypergraph/glossary_hook.py`): after an agent writes prose, it lints the new text and hands the agent an advisory note. Built and **not committed** (code, 41 tests, 28 probes; suite 857 passed); **registered** in `~/Projects/chi/.claude/settings.local.json` (personal, gitignored, not tracked).

**Decisions I took, and why**
- **Advisory, never blocking.** A wording helper must not stop work; the agent decides.
- **Quiet and fail-open.** Any error, a missing store or an unverified glossary prints nothing and exits 0 (errors are logged). Silence therefore means "nothing to say", not "checked and clean"; `status` says which.
- **Only the new text**, not the whole file, so old wording is not nagged about; code blocks, inline code and the glossary's own `_Avoid_:` lines are ignored; the glossary sources and change logs are skipped because they discuss the avoided words on purpose.
- **Ambiguity notes off by default**: every mention of "scope" would trigger one. Avoided words only.
- **A separate hook, in the local settings file.** `.claude/settings.json` already holds your jev-gate PreToolUse permission gate; I did not touch it. The lint hook merges alongside it, and removing it is deleting one key.

**Found while building it (a real bug):** `projection.project` and `define` crashed with "no such table: hyperedges" on a ledger that had never been migrated, instead of failing closed. Fixed in both (with a test); `lint` and the hook's `status` inherited the fix.

**Proven** by running the registered command exactly as Claude Code will: against the real, unverified prototype store it is silent; against a throwaway copy verified under a marked trial identity (deleted afterwards) it flagged `sign-off` (use Verification) and `workspace` (use Scope) and ignored `` `approval` `` in backticks.

**What I could not test:** a live Claude Code session. I tested the command, its JSON output and its exit codes, not Claude Code reading them. The output uses `hookSpecificOutput.additionalContext` for `PostToolUse`. **Claude Code reads hooks at session start, so restart the session after verifying the glossary and try it once.**

**Still yours:** verifying the prototype database; until then the hook is inert.

