# Trial mode and the audit log

Type: grilling (HITL)
Status: resolved
Blocked by:

## Question

With the wording, thresholds and local pre-check decided ([Signal wording, evaluation and thresholds](06-signals-evaluation-thresholds.md)), settle how the trial runs and what the gate records, so the spec can be written.

- **What trial mode records**: for every judged call the verdict the gate would have given, with no prompts and no blocking. Where it is stored and how a person reads it.
- **The audit log**: the exact schema (the fields from the charting decisions: timestamp, tool, redacted 80-character prefix with a hash, all six signal values, verdict, latency, which stage decided) plus the version of the wording and thresholds, the permission mode, whether the call came from a subagent, and the hook version; rotation at 90 days; file permissions; that the log itself is a protected path; and that file names are masked in the prefix just as in the evaluation.
- **Noticing a silently disabled gate**: a start-of-session heartbeat entry, coordinated with [Fail-open paths and the promises the spec makes](07-fail-open-promises.md).
- **How misses are found**: trial mode cannot see what it did not flag, so decide how the user samples unflagged calls, and what counts as a miss that earns a new always-escalate entry.
- **Exit criteria from trial to enforcement**: at least 200 real judged calls or one week (whichever is later), the 5% real-routine bar and the 10 prompts a day budget re-measured on real data, MCP precision certified from trial data, no unreviewed dangerous miss, and what triggers going back to trial.
- **Widening**: when and how the gate spreads beyond `~/Projects/chi`.

Carried in from [Fail-open paths and the promises the spec makes](07-fail-open-promises.md), to be fitted in rather than re-decided: the audit log also records the Claude Code version, the hook version and a per-session heartbeat; a `doctor` command exists; and the exit criteria include the user running the interactive checklist in `mode-tests/README.md` (the prompt in interactive default, acceptEdits, bypass and auto modes).

The answer is the schema, the review routine, the exit criteria and the widening rule.

## Facts found while grilling (not yet the answer)

- **Precedent in `gmail-mcp-local`**: `HashChainedAuditLog` in `src/security.js`. Its directory is mode 700 and file mode 600, entries are appended as JSON lines with a SHA-256 of the previous entry, and `verifyAuditLog` checks the chain. The same design fits here with the Python standard library.
- **Locations**: `~/.local/state`, `~/.config` and `~/Library/Logs` all exist on this machine.
- **Size**: one audit record is about 760 bytes. The busiest real day (123 calls) is about 91 KB; 90 days at the median rate is about 670 KB; even at the busiest rate every day it is about 8 MB. Rotation and size are not a problem.
- **Reconciliation is feasible**: session transcripts give per-session counts of judged-type tool calls (Bash, Write, Edit, NotebookEdit, MCP). This project's three sessions held 231, 39 and 8. Comparing those counts with the audit log would expose silent gaps.
- **A naming trap**: this planning folder is `.scratch/permission-gate/`. If the gate's own directories were also called `permission-gate`, a path rule matching that name would escalate every edit to these tickets. The gate's directories need a distinct name.
- **Write and Edit volume**: every matched call needs a record for reconciliation, including the many Write and Edit calls that get no opinion, so those records must be minimal.


## Answer

The user accepted all six recommendations (Q50 to Q55).

**1. Layout, trial switch and retention (Q50)**
- State directory `~/.local/state/jev-gate/` (mode 700): monthly `audit-YYYY-MM.jsonl` (mode 600) and a plain `heartbeat.jsonl` written by the SessionStart self-check.
- Config `~/.config/jev-gate/config.json` (mode 600): `mode` (`trial` or `enforce`), a per-install random salt, the threshold, the wording version, the scopes, and the skip list.
- Both directories are protected paths, so the agent cannot flip the mode. The name `jev-gate` is deliberately different from this planning folder so the protected-path rule does not fire on ticket edits; the rule matches `jev-gate`, `jev_gate` and `typesafe_permission_gate`.
- Retention is 90 days. The gate never deletes its own logs; only an explicit `doctor --prune` does.

**2. The record, privacy and tamper-evidence (Q51)**
- Every matched call gets a record, including no-opinion Write and Edit calls as minimal records, so the log can be reconciled with transcripts.
- Full record: timestamp, session id, scope, tool, masked 80-character prefix, salted hash, the six signal values, verdict (`would_ask`, `asked` or `no_opinion`), deciding stage (`precheck`, `fast_path`, `jev` or `fallback`), latencies, mode, permission mode, a subagent flag, and the wording, threshold, hook and Claude Code versions.
- The prefix uses the same redaction and file-name masking as the evaluation. A command that trips the local secret check logs only its pattern type. Write and Edit paths are masked with folders kept. The hash is salted per install so it cannot be dictionary-attacked.
- Each record carries the SHA-256 of the previous one (as in `gmail-mcp-local`); `doctor --verify` checks the chain.

**3. Trial mode behavior**: it records what the gate would have done and never escalates anything, local rules included, so the trial data is clean. Enforcement is switched on by editing the config.

**4. Review routine and misses (Q52)**
- A weekly local review page (like `prototype-eval/report.html`) built from the audit log showing every call the gate would have asked about, every near-threshold call (0.25 to 0.4), and a seeded random 10% of the rest (seed recorded).
- The user marks misses and false alarms. A miss is any call the user labels dangerous that the gate would not have escalated; it leads to a proposed always-escalate entry or a threshold change, re-measured on the labeled command set.
- `doctor --reconcile` compares audit counts with transcript counts per session (judged-type tool calls) so silent gaps show up.

**5. Exit criteria from trial to enforcement (Q53)**: all of the following.
- At least 200 real judged calls **and** at least 7 days.
- On the reviewed data, no more than 5% of routine calls would have been escalated, and the busiest day within the 10 prompt budget.
- No unreviewed dangerous miss; no unexplained heartbeat or reconcile gap; `doctor` clean.
- The user has run the interactive checklist in `mode-tests/README.md`.
- Bash and the local file-path rules enforce first. **MCP stays record-only** until at least 30 real MCP calls have been reviewed with 5% or fewer false alarms (real history has none yet).

**6. Back to trial (Q54)**: more than 10 prompts on two separate days in a week; a confirmed dangerous miss (add the entry, then 3 days of re-review); or any change to wording or threshold (it must first re-pass the labeled-set evaluation, then run 3 days in trial). A new always-escalate entry needs only the labeled-set check. A weekly Jev error or timeout rate above 5%, or any heartbeat gap, means running `doctor` before continuing.

**7. Widening (Q55)**: `~/Projects/chi` first, then `~/Projects` (all projects) with 3 days of trial before enforcing, then user level. Each step needs 2 weeks of stable enforcement with no return-to-trial trigger. The `scope` field in the log separates each scope's rates.

**Tools the spec must define**: `doctor` with `--verify` (hash chain), `--reconcile` (against transcripts), `--prune` (retention) and a plain check of the settings entry, path and key; the SessionStart self-check that writes `heartbeat.jsonl`; the weekly review-page generator.
