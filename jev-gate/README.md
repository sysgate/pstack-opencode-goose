# jev-gate

The Jev permission gate: a Claude Code PreToolUse hook that can only escalate. The design is in
[`docs/permission-gate/SPEC.md`](../docs/permission-gate/SPEC.md) (accepted, with amendments in section 13); the core
rule is [ADR 0001](../docs/adr/0001-permission-gate-only-escalates.md).

## Status: slices 1 to 7 are done; the gate is installed in TRIAL mode in `~/Projects/chi`

| Slice | State |
|---|---|
| 1. Launcher, shell fallback, `doctor` skeleton | built (`gate.py`, `doctor.py`) |
| 2. Local pre-check and its tests | built (`precheck.py`) |
| 3. Jev client, the six questions, fast path wired in | built (`jev.py`, `questions.py`) |
| 4. Config, trial mode, hash-chained audit log | built (`config.py`, `audit.py`, `sanitize.py`) |
| 5. Weekly review page, `doctor --reconcile` | built (`review.py`, `reconcile.py`) |
| 6. SessionStart self-check and heartbeat | built (`heartbeat.py`; consumers in `doctor.py`, `reconcile.py`, `review.py`) |
| 7. Install in `~/Projects/chi` in trial mode | done 2026-09-19: `.claude/settings.json` (both hooks), `~/.config/jev-gate/config.json` (trial, scope `chi`) |

**Installed (2026-09-19).** Trial mode: every matched call in `~/Projects/chi` sessions is judged and recorded in
`~/.local/state/jev-gate/`, and nothing is ever shown or blocked. Before leaving trial mode, run the interactive checklist in `mode-tests/README.md` (isolated scratch environment, about 20 minutes). Leaving trial mode means editing `config.json` by hand once
`python3 review.py --progress` shows the exit criteria met (at least 7 days and 200 judged Bash calls). The trial is counted from a start you set with `python3 review.py --start-trial` (default: the next local midnight; or `YYYY-MM-DD`); earlier records stay in the log but stop counting, and every change of the start is kept in `state/review/trial-start.jsonl`. A criterion with nothing counted yet reads NOT YET, never MET. To remove the gate,
delete `.claude/settings.json` (or its two hook entries). Note the pinned interpreter is the python.org build, which has no
CA certificates of its own; `jev.ssl_context()` falls back to `/etc/ssl/cert.pem`, and `doctor.py --live` tests through the
pinned interpreter so this cannot hide again.

**The self-check** (slice 6) is a `SessionStart` hook written as inline POSIX shell, so it does not depend on `gate.py` or the
interpreter it is checking. Each session start it verifies that the script is present, the pinned interpreter runs (3.9+),
the config file exists and a key is available (existence only, the value is never read), appends one line to
`heartbeat.jsonl`, and on any failure prints a `systemMessage`. It always exits 0. `doctor.py` shows the last heartbeat,
`--reconcile` adds a heartbeat column per session, and `review.py --progress` uses it for the exit criterion.
`doctor.py --reconcile --transcripts DIR` reads transcripts from another folder; use it whenever `JEV_GATE_HOME` points somewhere other than the
real home (as the checklist does), because transcripts otherwise are looked for under `$JEV_GATE_HOME/.claude/projects`.
Verified in two real headless sessions (claude 2.1.278, 2026-09-19): the hook runs at session start, the heartbeat
carries the real session id, and a failed check's `systemMessage` is parsed as hook output. Whether an interactive
session displays that message to the user is still unverified (step B1 of `mode-tests/README.md`); the heartbeat file is
the reliable record either way.

**What the gate does today** (if it were registered): for a matched call it runs the local rules, then the fast path,
then one Jev call (six yes/no questions, wording v2; escalate when any signal reaches the configured threshold, 0.4).
Write, Edit and NotebookEdit get the local protected-path check only. Every matched call is recorded in the audit log.
In `trial` mode nothing is ever printed; in `enforce` mode the ask is printed. Nothing in any settings file points at
this folder, and `~/.config/jev-gate` does not exist yet, so a registered gate would ask about everything until
`doctor.py --init` is run.

## Run the tests

    python3 -m pytest -q jev-gate/tests

The launcher tests run the real script on every Python found (3.9 and 3.12 here). Two regression tests compare the
pre-check with the local evaluation corpus under `.scratch/permission-gate/data/` and skip when it is absent.
No unit test touches your real config, your Keychain or the real API: every test runs against a throwaway
`JEV_GATE_HOME` (see `tests/conftest.py`), subprocess runs set `TYPESAFE_API_KEY=` and `JEV_GATE_NO_KEYCHAIN=1`, and
in-process tests fake the transport or use a local HTTP server.

    RUN_LIVE=1 python3 -m pytest -q jev-gate/tests/test_live.py -s   # real API, invented commands only, a few cents
    python3 jev-gate/doctor.py --live                                # one real call

## Config, trial mode and the audit log

- **Config**: `~/.config/jev-gate/config.json` (mode 600, directory 700): `mode` (`trial` or `enforce`), `threshold`,
  `wording`, a per-install random `salt`, `scopes` (name to directory prefix) and `skip_list` (MCP tools not judged).
  A missing, invalid or insecure config makes the gate ask (fail closed), even in a trial install. Change the mode
  by editing this file yourself; `doctor` has no switch for it on purpose.
- **State**: `~/.local/state/jev-gate/` (mode 700): monthly `audit-YYYY-MM.jsonl` (mode 600) and `claude_version.txt`.
  Both directories are protected paths (their names contain `jev-gate`), so the agent cannot rewrite them.
- **Trial mode** records the verdict the gate would have given (`would_ask`) and prints nothing, local rules included.
  A failure in trial mode is recorded, not shown; a script that cannot start at all still asks through the shell fallback.
- **The record** (one JSON line, each carrying the SHA-256 of the previous one): timestamp, session, scope, tool, a
  masked 80-character prefix (none at all for a command with a literal secret, only its pattern types), a salted hash,
  the six signal values, verdict (`would_ask`, `asked`, `no_opinion`), deciding stage, rule family, latencies, mode,
  permission mode, subagent flag, and the wording, threshold, hook and Claude Code versions. Write and Edit calls that get
  no opinion are minimal records.
- **A failed audit write** never changes the verdict; it writes one line to stderr and shows as a gap in reconciliation.

## The weekly review

    python3 review.py                              # a page for the last 7 days
    python3 review.py --since 2026-09-12 --until 2026-09-19
    python3 review.py --import-marks FILE          # marks copied from the page
    python3 review.py --progress                   # exit-criteria progress from the log and your marks

The page (`~/.local/state/jev-gate/review/review-*.html`, mode 600, inside the protected state directory, loads nothing
from the network) lists every call the gate would have asked about, every near-threshold call (highest signal from 0.25
up to the record's own threshold) and a seeded random 10% of the rest; the seed is printed and derived from the window, so
the sample is reproducible. Mark each call `dangerous` or `routine`, press **Copy marks**, save the text and import it.
A flagged call marked routine is a false alarm; an unflagged call marked dangerous is a miss. `--progress` then reports
each exit criterion: judged Bash calls (decided by Jev or a local rule) against 200, days of data against 7, busiest day of
would-be prompts against 10, every flagged call marked, the routine false-alarm rate against 5%, unreviewed dangerous
misses, the reconcile result, and the MCP rule (30 reviewed calls at 5% or fewer). `doctor is clean` and the interactive
checklist are manual. Marks are stored in `state/review/marks.jsonl`.

## Reconcile

    python3 doctor.py --reconcile [--since 2026-09-12]

Counts the tool calls the gate handles (Bash, Write, Edit, NotebookEdit, MCP) in Claude Code's session transcripts and
compares them per session with the audit log. Only calls from the first audit record onward count, sessions outside the
configured `scopes` are ignored, and subagent transcripts count toward their session. **OK**: equal. **WARN**: one call
missing (possibly in flight when the session ended). **FAIL**: two or more missing, or a session with transcript calls and
no records at all (was the gate running?). **INFO**: more records than transcript calls, or records with no transcript
(transcripts get cleaned up). It reads transcripts only to count calls and never stores or prints their content.

## doctor

    python3 doctor.py                 # interpreter, script, self-test, config, protected-path check, log chain, key
    python3 doctor.py --init          # create the config and state directories, in TRIAL mode; never overwrites
    python3 doctor.py --verify        # check the audit log hash chains
    python3 doctor.py --prune [--yes] # list (or delete) monthly logs older than 90 days
    python3 doctor.py --live          # also one real Jev call on an invented command
    python3 doctor.py --print-entry   # the settings entry to register in slice 7; prints only, writes nothing
    python3 doctor.py --settings FILE # also verify an installed entry against the spec

An agent running `doctor.py --init` or `--prune` through Bash is escalated
by the local pre-check ("gate maintenance command").

## Things to know while building

- **Standard library only, Python 3.9 or later**, POSIX (the deadline uses `signal.setitimer`, the log uses `flock`).
- **Fail closed**: every error, including a failed import, a bad event, a bad config or the 3 second deadline, becomes an
  `ask` whose reason shows only the exception type. If the script cannot start, the shell fallback in the hook command asks.
- **Reasons never contain matched text**: they name the rule and the pattern type, or the signals and their values.
- **What Jev receives**: the tool name and the sanitized command, nothing else. Sanitizing reproduces exactly what the
  evaluation applied (secret-like strings and emails redacted, file names under `/Volumes`, Downloads and Documents masked,
  folders kept), plus these choices made while building (recommendations accepted): the body of a data heredoc
  (`cat >> f <<EOF`) becomes a one-line marker; MCP arguments have every string value cut at 200 characters with all
  keys kept; the text is capped at 2000 characters. Real secret literals escalate locally and are never sent.
  Re-running the evaluation on exactly this text: 3.7 real routine commands falsely escalated per pass against 4.7 before,
  both real document overwrites still 0.77 or higher, 1 of 152 decisions changed (a false alarm went quiet), and the longest
  text sent was 1277 characters.
- **This folder is a protected path.** Once the gate is installed and enforcing, every write here escalates by design.
  Build with it uninstalled or in trial mode.
- `JEV_GATE_HOME` replaces `~` for the config and state locations (tests); doctor warns when it is set. `JEV_GATE_NO_KEYCHAIN=1`
  skips the Keychain and can only make the gate ask more.
- Still unverified (spec section 10): the `NotebookEdit` path field name (the launcher tries `file_path`, then
  `notebook_path`), and whether SessionStart's `systemMessage` reaches the user.
