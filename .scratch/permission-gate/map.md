# Map: Productionize the Jev permission gate

## Destination

A locked set of decisions and the build spec (`docs/permission-gate/SPEC.md`) from which the Jev permission gate can be built and rolled out, with nothing left to decide before someone builds it. The destination is the spec, not the installed gate.

## Notes

- **Domain**: a Claude Code PreToolUse hook that asks Jev for yes/no signals about Bash and `mcp__*` tool calls and can only escalate. Vocabulary is in `CONTEXT.md` (root of this folder); the core rule is `docs/adr/0001-permission-gate-only-escalates.md`.
- **Skills to consult**: `typesafe:typesafe-ai` (question wording, thresholds, confidence), `mattpocock-skills:domain-modeling` (keep `CONTEXT.md` current), `mattpocock-skills:research`.
- **Prototype to build from**: `typesafe_permission_gate.py` and its tests. The spec must list deltas from it: `deny` removed, four signals become six, timeout 12 s becomes 3 s, add the local pre-check (ordered before the fast path and Jev), match `Write`/`Edit`/`NotebookEdit` for the protected-path check, add the audit log.
- **Standing preferences**: real commands stay local and redacted, never full text in any log; nothing is sent to TypeSafe from a command containing a secret-like pattern; Jev never labels evidence; fail closed; independent of CHI/CCGF (no ledger writes); this folder is not a git repo, so no branches.
- **Tracker**: local markdown. Tickets are `issues/NN-slug.md` with `Type:`, `Status:`, `Blocked by:` lines.

## Decisions so far

<!-- one line per closed ticket -->

- [Charting decisions (Q1–Q18)](issues/01-charting-decisions.md): destination is spec-not-install; tripwire for agent mistakes and injection; Bash and MCP only; six signals; never allows or blocks; fail to ask; local-only redacted evidence; trial mode first; independent of CHI.
- [Hook behavior facts](issues/02-hook-behavior-facts.md): hooks fire in every mode and in subagents; `ask` prompts in default and auto mode (installed 2.1.278 is covered); a timeout, crash, exit 1, bad JSON or missing script all fail open; other modes and headless are unproven.
- [Extract and redact candidate commands](issues/03-extract-candidate-commands.md): 158 usable real Bash commands (39 with a dangerous-looking signal, 0 MCP calls) from 4 sessions, held locally; below the 200 bar and thin on volume and diversity, so the evidence gap is now its own ticket.
- [Close the evidence gap](issues/09-close-the-evidence-gap.md): real commands plus a tagged synthetic set (about 42 per-signal gap-fillers and about 30 MCP calls); precision on real commands only; pre-trial bar is 15 dangerous per signal all escalated and at most about 5% of real routine escalated, with the rule-of-three caveat (15/15 is about 80% recall at 95% confidence); trial mode re-measures before enforcement.
- [Write the synthetic command set](issues/10-write-synthetic-set.md): 84 tagged synthetic entries in `data/synthetic.jsonl` (42 dangerous Bash gap-fillers, 12 borderline routine Bash, 10 dangerous and 20 routine MCP calls; 24 borderline), no secret-pattern hits, no literal secrets on purpose; intended labels are proposals for the user to review.
- [Label the command set](issues/04-label-command-set.md): 158 real commands labeled (154 routine, 4 dangerous) and 84 synthetic, all user-reviewed, with the class rules for installs, third-party repos, disk mounts, document overwrites and temp deletes; per-signal shortfall of 34 goes to a second synthetic batch; file names are masked before anything is sent and nothing is approved to send yet.
- [Write the second synthetic batch](issues/11-write-second-synthetic-batch.md): 45 more reviewed synthetic entries (39 dangerous incl. 3 destructive MCP calls, 6 borderline routine) bring every signal to 16 or 17 dangerous examples, so the 15-per-signal bar is met with one entry of headroom; the review also caught a false positive in the secret-flag rule.
- [Assemble the spec](issues/13-assemble-the-spec.md): `docs/permission-gate/SPEC.md` written and accepted by the user; it indexes every decision, lists ten deltas from the prototype, states the limits and the unverified items, and suggests build slices. **The destination is reached.**
- [Trial mode and the audit log](issues/12-trial-mode-and-audit-log.md): state in `~/.local/state/jev-gate/`, config in `~/.config/jev-gate/` (both protected); hash-chained audit log with masked prefixes and a salted hash, every matched call recorded; trial mode never escalates; weekly review with a seeded sample and a `doctor --reconcile` against transcripts; exit criteria (200 calls and 7 days, 5% and 10-prompt bars, clean checks, interactive checklist), MCP record-only until 30 reviewed calls; return-to-trial triggers; staged widening.
- [Fail-open paths and the promises the spec makes](issues/07-fail-open-promises.md): the spec promises an ask whenever the gate decides or cannot run (shell fallback), and lists the four fail-open cases; supported and verified headless, documented-only interactive, unsupported `--bare`, `disableAllHooks` and Claude Code below 2.1.211; standard-library launcher with a pinned python.org interpreter, 5 second hook timeout, anchored matcher, SessionStart self-check, heartbeat and `doctor`; fallback verified in the real runner.
- [Test the unproven modes](issues/08-test-unproven-modes.md): headless tests on 2.1.278 show a hook `ask` overrides a matching allow rule, is honored in default, dontAsk, acceptEdits, bypassPermissions and plan mode (as a denial when nothing can prompt), fires in subagents with `agent_id`, and fails open on timeout; `auto` mode and the interactive prompt are unverified and left to an optional checklist.
- [Signal wording, evaluation and thresholds](issues/06-signals-evaluation-thresholds.md): wording v2 for six yes/no questions; the gate escalates when any signal reaches 0.4; one call per command; `claude plugin install`, `marketplace add` and `mcp add` become local always-escalate entries; measured 4.4% real routine escalated (bar 5%), all 95 dangerous caught, about 5.4 prompts on the busiest day; the 3 second ceiling holds (max 0.27 s). Optimistic because fitted to the same data; recall on real commands is unmeasured until trial mode.
- [Seed the local pre-check](issues/05-seed-local-pre-check.md): check order pre-check, fast path, Jev; escalate locally on literal secrets, secret-printing commands, `sudo`, `rm` on home/root, force-push, pipe-to-shell, and writes to protected paths (also for Write/Edit/NotebookEdit); the fast path stays a tiny prefix list; the list is capped at 30 entries and grows only from logged misses.

## Not yet specified


## Out of scope

- Installing the gate into any live settings (the destination is the spec).
- A shareable plugin for other people.
- CHI ledger integration or CCGF admission.
- Judging Write, Edit, NotebookEdit or WebFetch with Jev, or covering WebFetch at all; only a local protected-path check applies to Write, Edit and NotebookEdit (see [Seed the local pre-check](issues/05-seed-local-pre-check.md)); revisit after usage data.
- Defending against a determined attacker (the gate is a tripwire).
