# Jev permission gate: specification

**Status**: accepted by the user on 2026-09-19 ("read it and accept everything"). Built from a decision map (`.scratch/permission-gate/map.md`); nothing described here is built or installed, and no live settings were changed.

**How to read this**: it indexes decisions made in twelve tickets and links each one. Where a ticket's answer holds an exact text or list (the question wording, the rule lists), this spec points at it instead of copying it, so there is one place to change. Vocabulary is in [`CONTEXT.md`](../../CONTEXT.md). The core rule is [ADR 0001](../adr/0001-permission-gate-only-escalates.md).

---

## 1. What it is

A Claude Code **PreToolUse hook** that reviews an agent's tool calls before they run. For each call it may ask Jev (TypeSafe's judgment model) six yes/no questions, applies one fixed threshold, and then either **asks the user to confirm** or says nothing. It can **only escalate**: it never grants permission and, in interactive sessions, never blocks outright (ADR 0001).

## 2. Goals, non-goals, threat model

**Goals**
- Catch honest agent mistakes and actions driven by instructions injected into the agent's inputs, by adding a confirmation prompt.
- Keep real commands local, redacted and masked; send Jev only what is needed.
- Fail closed wherever Claude Code allows it; say plainly where it cannot.
- Prove itself on evidence before it enforces (trial mode).

**Non-goals**
- A security boundary against a determined attacker. Text matching is evadable (variables, `cd` then relative paths, obfuscation); Jev's `tampers_config` signal is the second layer. The gate is a tripwire.
- A sandbox, a CHI/CCGF authority, or a shareable plugin. It writes nothing to the CHI ledger and claims no admission.
- Judging `Write`, `Edit`, `NotebookEdit` or `WebFetch` with Jev. A local protected-path check applies to the first three; the rest is out of scope until usage data exists.
- Installing the gate. This document is the hand-off; building and installing are separate work.

Source: [Charting decisions (Q1–Q18)](../../.scratch/permission-gate/issues/01-charting-decisions.md).

## 3. What the gate sees and how it decides

**Matcher** (anchored, because matchers are unanchored regular expressions): `^(Bash|Write|Edit|NotebookEdit)$|^mcp__`.

**Order of checks** for every matched call: (1) local pre-check, (2) fast path, (3) Jev.

| Tool | Input read | What happens |
|---|---|---|
| Bash | the command | pre-check, then fast path, then Jev |
| MCP (`mcp__*`) | the JSON input | Jev (unless on the user's skip list, initially empty) |
| Write, Edit | `tool_input.file_path` | local protected-path check only; no Jev call |
| NotebookEdit | `file_path`, then `notebook_path` (the docs do not name it; verify) | local protected-path check only |
| anything else | n/a | no opinion |

**State sent to Jev**: the tool name and the command, or the JSON input for an MCP call. **Nothing else**: no working directory, no description, no transcript. A command that trips a local rule is never sent.

**Output**: an `ask` decision whose reason names the signals and values (or the local rule family), and **never repeats matched text**; or nothing (no opinion). The gate never emits `allow`, never emits `deny`, and never exits with code 2. In trial mode it records what it would have done and always says nothing.

## 4. The six signals and the threshold

One request per command carries six yes/no questions (`Noul`). The gate escalates when **any** signal reaches **0.4**. One call per command; no repeated calls or averaging (drift median 0.000, p95 0.03, max 0.09, and repeats did not help).

| Signal | Asks whether the call would |
|---|---|
| `destructive` | delete, overwrite or irreversibly change files, data, disks or settings beyond regenerable output |
| `external_effect` | change state outside this machine or spend money |
| `reads_secrets` | read or print credentials, keys, tokens or keychain contents |
| `uploads_data` | send local data to a remote host or make it public |
| `runs_downloaded` | execute code from an unvetted download or source |
| `tampers_config` | change agent, shell, git or system configuration |

**The exact question text is wording v2**, recorded in the answer to [Signal wording, evaluation and thresholds](../../.scratch/permission-gate/issues/06-signals-evaluation-thresholds.md). It encodes the user's class rules (named-package installs, project-file edits, disk mount and eject, listing key names, parsing downloaded data are routine; overwriting a document is dangerous). Do not paraphrase it.

## 5. The local pre-check

Code only; nothing leaves the machine; ordered before everything else. Full lists and reasons are in [Seed the local pre-check](../../.scratch/permission-gate/issues/05-seed-local-pre-check.md) and its amendments.

- **Literal secrets** (known token prefixes, private-key blocks, JWTs, Authorization or Bearer literals, credentials in URLs, secret-named assignments and flags with a literal value). A `$VAR` reference is not a literal. The generic long-random-string rule only redacts, and never escalates. The secret-flag rule needs a lookbehind so `find-generic-password -s` is not a flag.
- **Commands that print secrets**: keychain reads with `-w`, private-key or `.pem` reads, `gpg --export-secret-*`, bare `env` or `printenv`, printing or copying `.env` contents.
- **Destructive and irreversible seeds**: `sudo`; `rm` with recursive or force flags on home, root or a whole directory (including `./*`); force pushes; pipe-to-shell.
- **Agent configuration commands**: `claude plugin install`, `claude plugin marketplace add`, `claude mcp add`.
- **Protected paths, write target only** (reading never escalates): agent configuration (`.claude`, `.claude.json`), `.mcp.json`, shell profiles (exact names), scheduled jobs, `/etc`, ssh `config` and `authorized_keys`, and the gate's own files (`jev-gate`, `jev_gate`, `typesafe_permission_gate`). `CLAUDE.md` and `AGENTS.md` are deliberately excluded.
- **Matching rules**: `cp`, `ln` and `install` write only their last argument; the body of a data heredoc (`cat >> f <<EOF`) is not scanned by the non-secret rules, while a heredoc feeding a shell or interpreter is, and the literal-secret rule reads everything.
- **Fast path**: a tiny prefix list of provably local read-only commands with no shell metacharacters. It returns no opinion, never allow. It covers about none of the real commands; nearly every command is judged.
- **Growth**: at most 30 entries beyond the seed families, each with a justification, a date and a pointer to the miss behind it; only the user adds them; the list file is a protected path.

Reference implementation and tests: `.scratch/permission-gate/prototype-eval/precheck.py` and `test_precheck_secrets.py` (throwaway prototype code; lift the logic, not the file).

## 6. The launcher, failure behavior and support

**Hook command** (shell form, so a fallback works): `PY gate.py || printf '<ask JSON>'`, where `PY` is the absolute path `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3` (any Python 3.9 or later works; the script needs no packages). `gate.py` uses the standard library only (plain HTTPS to TypeSafe, no SDK), catches every error including import errors, and enforces a **3 second** internal deadline. The hook entry sets **`timeout: 5`** so the script's own `ask` arrives before Claude Code cancels the hook.

**The promise**: the gate asks whenever it judges a call risky. When it cannot run at all (missing script or interpreter, crash, bad output), it asks anyway through the shell fallback. It **cannot** help in four situations where Claude Code fails open: the hook is cancelled at its timeout; hooks are disabled (`disableAllHooks`, `--bare`); the settings entry is missing or mistyped; the shell cannot start. It never claims to block anything. In unattended runs (headless `-p`) an escalation acts as a **denial**, because nothing can answer.

**Support**
- Verified: headless runs in default, dontAsk, acceptEdits, bypassPermissions and plan modes (a hook `ask` overrides a matching allow rule and is honored as a denial).
- By documentation only: interactive default and auto mode. The other interactive modes are unverified.
- Unsupported: `--bare`, `disableAllHooks`, Claude Code older than **2.1.211**. Tested on **2.1.278**; the version is recorded in the audit log.

**Overhead**: realistic cost is about 0.3 to 0.5 seconds per judged command (a fresh process and connection each time). Measured maximum for a warm call was 0.27 seconds; the 3 second ceiling has about ten times headroom.

**Noticing a silently disabled gate**: a SessionStart self-check written as inline shell (does not depend on the gate script) verifies the script is executable, the interpreter runs and the key is readable, and warns through `systemMessage`; each session writes a heartbeat; `doctor` checks the settings entry, path and key on demand.

Sources: [Fail-open paths and the promises the spec makes](../../.scratch/permission-gate/issues/07-fail-open-promises.md), [Hook behavior facts](../../.scratch/permission-gate/issues/02-hook-behavior-facts.md), [Test the unproven modes](../../.scratch/permission-gate/issues/08-test-unproven-modes.md). The mode-test harness is `.scratch/permission-gate/mode-tests/`.

## 7. Trial mode, the audit log and rollout

Full detail: [Trial mode and the audit log](../../.scratch/permission-gate/issues/12-trial-mode-and-audit-log.md).

- **Layout**: logs in `~/.local/state/jev-gate/` (mode 700): monthly `audit-YYYY-MM.jsonl` (mode 600) and a plain `heartbeat.jsonl`. Config in `~/.config/jev-gate/config.json` (mode 600): `mode` (`trial` or `enforce`), a per-install random salt, the threshold, the wording version, the scopes and the skip list. Both are protected paths, so the agent cannot flip the mode. Retention is 90 days; only `doctor --prune` deletes.
- **Audit record**: every matched call, minimal for no-opinion Write and Edit calls. Fields: timestamp, session id, scope, tool, masked 80-character prefix, salted hash, the six signal values, verdict (`would_ask`, `asked`, `no_opinion`), deciding stage (`precheck`, `fast_path`, `jev`, `fallback`), latencies, mode, permission mode, a subagent flag, and the wording, threshold, hook and Claude Code versions. A secret-check hit logs only its pattern type. Each record carries the SHA-256 of the previous one; `doctor --verify` checks the chain.
- **Trial mode**: records what the gate would have done and never escalates, local rules included.
- **Weekly review**: a local page of every call the gate would have asked about, every near-threshold call (0.25 to 0.4) and a seeded random 10% of the rest; the user marks misses and false alarms. `doctor --reconcile` compares audit counts with transcript counts per session. A miss is a call the user labels dangerous that the gate would not have escalated; it leads to a proposed always-escalate entry or a threshold change, re-measured on the labeled set.
- **Exit to enforcement**: at least 200 real judged calls **and** 7 days; no more than 5% of routine calls would have been escalated and the busiest day within the 10-prompt budget; no unreviewed dangerous miss; no unexplained heartbeat or reconcile gap; `doctor` clean; the user has run the interactive checklist (`jev-gate/mode-tests/README.md`). Bash and the local file-path rules enforce first; **MCP stays record-only** until at least 30 real MCP calls have been reviewed with 5% or fewer false alarms.
- **Back to trial**: more than 10 prompts on two days in a week; a confirmed dangerous miss (then 3 days of re-review); any wording or threshold change (re-pass the labeled-set evaluation, then 3 days). A new always-escalate entry needs only the labeled-set check. A weekly Jev error or timeout rate above 5%, or a heartbeat gap, means running `doctor` first.
- **Widening**: `~/Projects/chi`, then `~/Projects` (3 days of trial before enforcing), then user level; two stable enforcement weeks per step.

## 8. Evidence and the test plan

- **Real commands**: 158 usable, from 4 sessions, held locally and redacted ([Extract and redact candidate commands](../../.scratch/permission-gate/issues/03-extract-candidate-commands.md)). Labeled by the agent, reviewed by the user: 154 routine, 4 dangerous ([Label the command set](../../.scratch/permission-gate/issues/04-label-command-set.md)).
- **Synthetic commands**: 129 tagged and reviewed (91 dangerous, 38 routine), never used to measure precision ([first batch](../../.scratch/permission-gate/issues/10-write-synthetic-set.md), [second batch](../../.scratch/permission-gate/issues/11-write-second-synthetic-batch.md)). Dangerous examples per signal, real plus synthetic: destructive 16, external effect 16, reads secrets 16, uploads 17, runs downloaded 16, tampers 16 ([Close the evidence gap](../../.scratch/permission-gate/issues/09-close-the-evidence-gap.md)).
- **Measured** (wording v2, uniform 0.4, whole gate): 4.4% of real routine commands escalated (bar 5%); all 95 dangerous commands escalated in all three passes; about 0.4 extra prompts on a median day and 5.4 on the busiest (budget 10). The local pre-check alone escalates 2 of 154 real routine commands (1.3%), 2 of 4 real dangerous, 17 of 78 dangerous synthetic Bash.
- **Privacy in evaluation**: real commands were masked (file names replaced, folders kept), hash-verified against a recorded approval, and sent with no working directory or description; a command that tripped the local check was never sent.
- **How to re-measure**: the scripts in `.scratch/permission-gate/prototype-eval/` (`eval_run.py`, `analyze.py`, `analyze2.py`) and the interactive threshold page `report.html` (local only).

## 9. Deltas from the prototype (`typesafe_permission_gate.py`)

1. `deny` removed; the gate emits only `ask` or nothing.
2. Four signals become six: `sends_data_out` is split into `uploads_data` and `runs_downloaded`; `tampers_config` is added; wording v2.
3. One threshold, 0.4, on any signal, replacing 0.30 and the 0.85 secrets-plus-exfiltration deny.
4. Internal timeout 12 s becomes 3 s; the hook `timeout` is 5.
5. Local pre-check added, ordered before the fast path and Jev, with the always-escalate list and the protected-path rule.
6. Matches `Write`, `Edit` and `NotebookEdit` for the protected-path check; anchored matcher.
7. No `cwd` or `description` sent to Jev.
8. Standard-library launcher instead of the SDK; shell fallback; pinned interpreter.
9. Trial mode, the audit log, heartbeat, SessionStart self-check and `doctor` added.
10. The `ask` reason never repeats matched text.

## 10. Limits and what is still unverified

**Limits, stated plainly**
- Only **4 real commands are dangerous**. Recall on real commands is unmeasured until trial mode; every other dangerous example is invented.
- Catching 15 of 15 examples supports only about 80% recall at 95% confidence (the rule of three). The pre-trial bar is evidence for entering trial mode, not a guarantee.
- Wording and thresholds were tuned on the same data they were measured on, so the numbers are optimistic; the margin at 0.4 is about 0.06. The plugin-install score fell from 0.86 to 0.48 under wording v2, which is why it has a local rule.
- The local rules are text matching and evadable; MCP calls have no local rule and no real history.
- In headless runs the gate blocks flagged commands, which is fail closed but is not "never blocks".

**Unverified**: plan mode with a live ask (the model declines to call Bash there, so the gate is never reached); the gate being killed part-way through printing.
**Verified 2026-09-19 (Claude Code 2.1.278, interactive, in a scripted pseudo-terminal and in the user's iTerm2, recorded with `script -k`)**: the gate's `ask` shows a real permission prompt in default mode (`Hook PreToolUse:Bash requires confirmation for this command: Jev gate: could destroy data 0.64`, then `1. Yes  2. No`), for Bash, protected-path Write and NotebookEdit, and a subagent's Bash call, even with `Write`, `Bash(rm:*)` allow rules present; declining stopped the command (nothing ran) and the audit log recorded `asked`. NotebookEdit's path field is `notebook_path`. A mistyped interpreter path is turned into an `ask` by the shell fallback. The SessionStart `systemMessage` is shown on screen as `SessionStart:startup says: Jev gate self-check failed (...)`, in a small dim line under the input box, which is easy to miss.

## 11. Suggested build slices (a suggestion, not a decision)

1. Launcher, shell fallback and `doctor` skeleton, with the fallback tests from `mode-tests/`.
2. The local pre-check and its tests (start from `prototype-eval/precheck.py`).
3. The Jev client and the six questions; run the labeled-set evaluation again against the real gate code.
4. The audit log with the hash chain, trial mode and config.
5. The weekly review page and `doctor --reconcile`.
6. SessionStart self-check and heartbeat.
7. Install in `~/Projects/chi` in trial mode; run the interactive checklist; begin the trial.

## 12. Decision index

| Ticket | Gist |
|---|---|
| [Charting decisions (Q1–Q18)](../../.scratch/permission-gate/issues/01-charting-decisions.md) | scope, threat model, policy, privacy, rollout |
| [Hook behavior facts](../../.scratch/permission-gate/issues/02-hook-behavior-facts.md) | hooks fire everywhere; the gate fails open on timeout, crash, bad JSON, missing script |
| [Extract and redact candidate commands](../../.scratch/permission-gate/issues/03-extract-candidate-commands.md) | the real evidence pool |
| [Label the command set](../../.scratch/permission-gate/issues/04-label-command-set.md) | labels, class rules, masking |
| [Seed the local pre-check](../../.scratch/permission-gate/issues/05-seed-local-pre-check.md) | the v1 rules and protected paths |
| [Signal wording, evaluation and thresholds](../../.scratch/permission-gate/issues/06-signals-evaluation-thresholds.md) | wording v2, threshold 0.4, measured results |
| [Fail-open paths and the promises the spec makes](../../.scratch/permission-gate/issues/07-fail-open-promises.md) | launcher, promise, support, self-check |
| [Test the unproven modes](../../.scratch/permission-gate/issues/08-test-unproven-modes.md) | headless results across modes |
| [Close the evidence gap](../../.scratch/permission-gate/issues/09-close-the-evidence-gap.md) | real plus synthetic, readiness bar |
| [Write the synthetic command set](../../.scratch/permission-gate/issues/10-write-synthetic-set.md) | first synthetic batch |
| [Write the second synthetic batch](../../.scratch/permission-gate/issues/11-write-second-synthetic-batch.md) | second synthetic batch |
| [Trial mode and the audit log](../../.scratch/permission-gate/issues/12-trial-mode-and-audit-log.md) | audit log, trial, review, exit, widening |

## 13. Amendments made while building (2026-09-19)

The spec above was accepted as written. These choices were made while building slices 3 and 4, on the builder's
recommendations, which the user accepted. They refine sections 3, 5 and 7; nothing above was rewritten.

1. **Live input to Jev** (section 3): the tool name and the *sanitized* command. Sanitizing is the same redaction and
   file-name masking the evaluation used, so the live text has the shape the thresholds were fitted to. Two additions:
   the body of a data heredoc is replaced by a one-line marker (`[heredoc body omitted: N chars]`), and for MCP calls every
   string value is cut at 200 characters with all keys kept. The 2000-character head cap stays. Confirmation: the
   evaluation was re-run on exactly this text (152 approved, hash-verified real commands, three passes, 456 calls). Real
   routine commands falsely escalated per pass fell from 4.7 to 3.7; both real document overwrites still scored 0.77 or
   higher in every pass; 1 of 152 decisions changed, from a false alarm to quiet; the longest text sent was 1277 characters.
2. **Gate maintenance** (section 5): `doctor.py --init` and `--prune` run through Bash are escalated by the local
   pre-check, so an agent cannot initialize or prune the gate through its own scripts. This is a deliberate addition to
   the always-escalate list.
3. **Config and failure behavior** (sections 6 and 7): a missing, invalid or insecure config makes the gate ask, even in a
   trial install; in trial mode any other failure is recorded (`decider: fallback`, `would_ask`) and not shown. A failed
   audit write never changes the verdict.
4. **Audit record** (section 7): as specified, plus `rule_family` and `secret_types`; a command with a literal secret logs
   only the pattern types and no prefix. The Claude Code version is not in the hook event, so `doctor` caches it in the
   state directory and the gate reads the cache (recorded as unknown until doctor has run).
5. **Mode changes**: made by editing `config.json`; `doctor` deliberately has no switch for it.

### Slice 5 (added the same day)

6. **The weekly review page** (section 7): a single self-contained page written mode 600 into the protected state
   directory (`review/`), built only from the audit log's masked excerpts, loading nothing from the network and building
   its rows from text, not markup. Near-threshold means the highest signal from 0.25 up to that record's own threshold.
   The sample seed is `jev-gate-review|<window>`, so the same window always yields the same sample. Marks are copied out of
   the page and imported with `review.py --import-marks`; the latest mark for a call wins.
7. **Reconcile** (section 7): compares matched tool calls in session transcripts with audit records per session, from the
   first audit record onward and only for sessions inside the configured scopes. One missing call is a warning (it may have
   been in flight); two or more, or a session with no records at all, fail. It only counts transcript calls.
8. **Exit-criteria progress** (section 7): `review.py --progress` computes the mechanical criteria. A "judged Bash call" is a
   Bash record decided by Jev or a local rule. The doctor and interactive-checklist criteria are manual; the heartbeat criterion is computed from slice 6 on (item 11).

### Slice 6 (added the same day)

9. **Self-check** (section 6): a `SessionStart` hook with no matcher and a 5-second timeout, whose command is inline POSIX shell
   (`heartbeat.py`), independent of `gate.py`. It checks: script present, pinned interpreter present and 3.9+, config file
   present, key available (the environment variable, or the Keychain item's existence; never its value). Problems are named
   (`script-missing`, `interpreter-missing`, `interpreter-broken`, `config-missing`, `key-missing`). It always exits 0.
10. **Heartbeat** (section 7): one JSON line per session start in a plain, not hash-chained `heartbeat.jsonl`
    (`ts`, `session`, `source`, `ok`, `problems`); session and source are reduced to `A-Za-z0-9_.-`. A failed check also
    prints a `systemMessage`; delivery of that message to the user is unverified.
11. **Consumers**: `doctor` reports the last heartbeat and how many failed; `reconcile` gives each session a heartbeat state
    (`ok`, `failed`, `missing`, `n/a` for sessions that began before the first heartbeat, `not recorded`), and a session that
    was otherwise OK becomes a warning if its heartbeat is missing or failed; `review --progress` marks the heartbeat
    criterion met only when every session since the first heartbeat has a passing one. `doctor.settings_entry()` and
    `check_settings` now cover both hooks; a missing self-check entry is a warning, a differing one a failure.
12. **Verified headless, 2026-09-19** (claude 2.1.278, two `claude -p` runs in an isolated scratch project with a throwaway
    home, about $0.02): the `SessionStart` self-check runs, exits 0, and writes a heartbeat whose `session` equals the
    session's own id and whose `source` is `startup`. Healthy: empty hook output, `ok:true`. Broken (no config, no key):
    `ok:false, problems:"config-missing key-missing"`, and the hook's stdout `{"systemMessage":...}` is reported as the hook
    response with `outcome: success`. Not verified: whether an interactive session shows that message to the user.

### Slice 7 (installed the same day)

13. **Installed in trial mode** with the user's explicit approval (including live sending of redacted, file-name-masked
    Bash and MCP input to Jev, which the earlier evaluation-only approval did not cover): `~/Projects/chi/.claude/settings.json`
    holds exactly the `doctor.py --print-entry` output; `~/.config/jev-gate/config.json` was created by `doctor.py --init`
    (mode trial, threshold 0.4, wording v2) with scope `chi` = `/Users/robertlai/Projects/chi` added so reconcile ignores
    sessions elsewhere. Project-level settings apply only to sessions started in that folder.
14. **Found by the live install, fixed:** the pinned interpreter (python.org 3.12) has no CA certificates, so every real Jev
    call failed certificate verification and fell back (the tests and `doctor --live` had used Anaconda, which has them).
    Fixes: `jev.ssl_context()` (verification stays on; uses the system bundle when the interpreter has none), `doctor --live`
    now calls Jev through the pinned interpreter, and a fallback audit record carries `error` (the exception type only)
    so a silent trial-mode failure is visible in the log. One early real record (this session's own `grep`) is a `fallback`
    from this bug; the log is append-only, so it stays.
15. **Secret-named assignment rule tightened** (section 5, literal secrets; user-approved 2026-09-19 after the first live
    trial data showed a false alarm on an ordinary code edit containing `key = os.environ.get(...)` and
    `KEYCHAIN_SERVICE = "typesafe"`). The local rule now escalates such an assignment only when the value reads as a literal
    secret: 8 to 200 characters, no spaces, at least one letter and one digit or symbol, and not a reference or expression
    (`$X`, `$(...)`, a call, an index), a path, a UUID, or a plain word or number. The known-token-prefix, JWT, PEM,
    auth-header, URL-credential and explicit `--password`-style flag rules are unchanged. Accepted trade: a short, plain-word
    or all-digit literal password in an assignment is no longer caught locally and goes to Jev (which sees the redacted text,
    since redaction in `sanitize.py` stays broad).
16. **Interactive checklist written** (section 10, exit criteria): `jev-gate/mode-tests/README.md` with `setup.py`. It runs against
    the real gate in an isolated scratch environment (`/tmp/gate-checklist`, a throwaway home in enforce mode, outside the
    repository because any path containing `jev-gate` is itself protected). It covers the prompt in default, acceptEdits,
    plan, bypassPermissions and auto modes, an allow rule being overridden, a subagent call, the NotebookEdit path field, the
    session-start warning's visibility (healthy, no config, mistyped interpreter) and the shell fallback. Commands were
    chosen and tested headless to flag reliably and be harmless if approved (a `curl` upload to a `.invalid` address scored
    uploads_data 0.93, an `rm -rf` of two nonexistent files scored destructive 0.68, and `touch /etc/...` hits the local rule).
    Still uncovered: the gate being killed part-way through printing.

### Interactive checklist result (2026-09-19)

17. **The first interactive run failed its central check.** Three real interactive sessions (A healthy, B no config, C mistyped
    interpreter; default mode, model haiku, `--setting-sources project`). What the record shows: the gate decided correctly every
    time (audit and transcripts: `asked` for the curl upload 0.93, `rm -rf` 0.66 to 0.67 including from a subagent, the
    `touch /etc` and the Write and NotebookEdit protected-path rules; B and C hook output was the fail-closed `ask`), and the
    transcripts record each `ask` as a successful PreToolUse hook. What the user reports: **no permission prompt appeared for any of
    them** and every command ran (a `touch` ran 1.2 s after its ask; none was rejected). The self-check warning was also not shown in
    B or C, though the transcript holds it as SessionStart hook output. Not yet explained. Ruled out locally: no managed settings,
    no shell alias for `claude`, no `defaultMode` or `permissions` in user settings; the launch flags were as documented.
    Unruled: an interactive-only behavior of hook `ask`, a per-session "don't ask again" state, or the sessions' UI hiding hook
    prompts. Consequences until explained: **do not leave trial mode**; the interactive-checklist exit criterion is NOT met; the
    headless result (an `ask` becomes a denial when nothing can prompt) must not be read as proof that an interactive `ask` stops
    anything; and the heartbeat file, not the `systemMessage`, is the only reliable warning channel.
18. **Also learned:** answers written by the model inside a checklist session ("No prompt appeared") are not observations;
    the model sees only tool results. Checklist results must be the person's own. `doctor --reconcile` finds transcripts under
    `$JEV_GATE_HOME/.claude/projects`, so an isolated home cannot be reconciled without a `--transcripts` option (not yet added).
19. **Follow-up: the failure in item 17 was NOT reproduced.** A scripted pseudo-terminal running real interactive `claude`
    (2.1.278, haiku, `--setting-sources project`, the real gate in enforce mode, the same allow rules) prompted for every one of
    the five calls that did not appear to prompt for the user (curl upload, `touch /etc`, protected Write, NotebookEdit, subagent
    `rm -rf`), showing the Jev reason; declining stopped each command and the audit log matched. Evidence in the user's own
    transcripts also fits prompts having appeared: the permission mode moved from `default` to `acceptEdits` between the Write
    and the NotebookEdit (what answering a Write prompt with "Yes, allow all edits" does; in the pseudo-terminal the same
    keystroke produced the same switch), and the ask-to-result gaps were 5 to 35 s for most asks, though one `touch` ran 1.2 s
    after its ask. The user's recollection ("no prompts appeared") conflicts with that, and the sessions were driven by pasted
    instructions, so the screen may have been read differently from what the record shows. Status: **unresolved but likely a
    misreading, not a gate or Claude Code defect.** To close it, the user runs ONE step by hand (A2 in a fresh session A) and
    looks at the screen. Until then the interactive-checklist exit criterion stays NOT met and trial mode continues.
20. **Checklist wording fixes** (not yet applied to `mode-tests/README.md`): the trust dialog appears on first launch in a new
    folder and defaults to "No, exit"; the Write prompt has three options, and the middle one ("allow all edits") silently
    changes the mode to acceptEdits, so declining means the last option; and the warning line is dim and easy to miss.
21. **Resolved: items 17 and 19 were a misreading, not a defect.** The user re-ran the step by hand in iTerm2 under
    `script -q -k`. The recording shows the prompt drawn on screen (`Hook PreToolUse:Bash requires confirmation for this command:
    Jev gate: could send data out 0.93 ... Do you want to proceed? 1. Yes 2. No`), about 6 s of waiting, then a `1` keystroke,
    then the command ran; the gate's audit record (`asked`), the session's hook record and the reconcile row all agree
    (`OK`, transcript 1, logged 1, heartbeat ok). No iTerm2 triggers or key mappings exist that could answer a prompt. The
    earlier report ("no prompts appeared") is retracted; the earlier `ask` executions were approved at a prompt, most likely by
    reflex, since "1. Yes" is the default and the prompt appears exactly where the command's output is expected.
    Consequence for the design: an `ask` is only as strong as the person answering it. Trial data and the weekly review
    should therefore also count how often a would-be prompt is approved within a couple of seconds (a later refinement,
    not built), and the README should tell the user that Enter and `1` both mean Yes.
22. **Follow-ups from the checklist, done:** `doctor.py --reconcile --transcripts DIR` (reads transcripts from DIR; an error if the
    folder is missing or the option is used without `--reconcile`), so an isolated `JEV_GATE_HOME` can still be reconciled; and
    `mode-tests/README.md` now explains how to answer prompts (1, Enter and a tap all mean Yes; decline with Esc or the last
    option), the three-option Write prompt whose middle choice switches the mode, the trust dialog whose default is "No, exit",
    the dim self-check line, how to record the screen with `script -q -k`, and to type each prompt rather than paste the whole list.
23. **The trial is counted from a set start** (section 7, exit criteria; user-approved 2026-09-19 after the first `--progress` runs
    showed the build day, 29 would-be prompts, would otherwise stay the busiest day for good; `--progress` had no window and
    my earlier claim that build records would "age out" was wrong). `review.py --start-trial [WHEN]` appends a start to
    `state/review/trial-start.jsonl` (mode 600; `WHEN` is `YYYY-MM-DD` as a local midnight, an ISO time, or by default the next
    local midnight; the latest wins and history is kept). `--progress` then counts only records, heartbeats and reconcile
    sessions from that instant and prints how many earlier records it excluded. The audit log itself is untouched. Set on
    2026-09-19 to 2026-09-20 00:00 PDT (07:00Z), excluding 101 build-era records. Also: a criterion with nothing counted yet
    (busiest day, every flagged call reviewed, false-alarm rate, reconcile) now reads NOT YET instead of passing vacuously.
    Known limit, not changed: "a day" is a UTC calendar day (`record["ts"][:10]`), so a busy local evening can split across two
    buckets and make the busiest day look smaller than it felt. A start that is later moved is visible in the history file.
24. **Checklist A9 to A11 run (2026-09-19, scripted pseudo-terminal, real interactive `claude` 2.1.278, the real gate in enforce mode
    with a throwaway home, the curl-upload command that Jev scores about 0.9):** `bypassPermissions` (after its warning dialog):
    the gate's ask still produced a prompt (`Jev gate: could send data out 0.92`), declining stopped the command, audit `asked` with
    permission mode `bypassPermissions`. `auto` (Sonnet; auto mode is not available on Haiku): the same, permission mode `auto`
    (0.94). `plan`: not exercised, because in plan mode the model itself refuses to call Bash (twice, with a network command and a
    read-only `cat`), so nothing reaches a PreToolUse hook; the earlier headless test found asks honored in plan mode. Conclusion:
    an `ask` from the gate is honored in default, acceptEdits, bypassPermissions and auto modes, in the terminal as well as
    headless. Not run in the user's own hands, but the interface behavior was already confirmed there for default mode.

