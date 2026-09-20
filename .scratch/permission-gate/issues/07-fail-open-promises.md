# Fail-open paths and the promises the spec makes

Type: grilling (HITL)
Status: resolved
Blocked by: 08

## Question

The gate cannot block when it is broken (see [Hook behavior facts](02-hook-behavior-facts.md)): a timeout, crash, import error, exit 1, bad JSON or mistyped script path all fall through to normal permissions. With the empirical results from [Test the unproven modes](08-test-unproven-modes.md), decide what the spec promises and how the design narrows the gap:

- The facts now in hand from [Test the unproven modes](08-test-unproven-modes.md): in headless runs an escalation is a denial, `bypassPermissions` is still gated, the hook fires in subagents, and a slow hook fails open; interactive prompts and `auto` mode remain documented but unverified.
- The guarantee wording (for example: it asks when it decides to; it never claims to block when broken).
- Which permission modes and run types v1 officially supports, and how unsupported ones (bypassPermissions, headless, and whatever ticket 08 shows fails) are stated.
- The launcher design: a small standard-library-only entry point that catches import errors and internal deadlines and still emits `ask`, with an internal ceiling below the hook's explicit `timeout` setting.
- How a silently disabled gate is noticed (a mistyped path, a missing key, a stalled hook), for example a start-of-session self-check and an audit-log heartbeat.
- How the launcher handles `Write`, `Edit` and `NotebookEdit` inputs (a `file_path`, no command) for the local protected-path check.
- The hook's explicit `timeout` value: it must sit above the 3 second internal ceiling (decided in [Signal wording, evaluation and thresholds](06-signals-evaluation-thresholds.md)) so the launcher emits `ask` before Claude Code cancels the hook and fails open.
- The minimum Claude Code version the spec requires.

The answer is the promises, the supported-modes list, and the launcher and self-check decisions.

## Facts found while grilling (not yet the answer)

- **Hook commands run through a shell** (`sh -c` on macOS) when the entry has no `args`, so `||`, pipes and redirects work. The exec form (`command` plus `args`) uses no shell and so cannot express a fallback. A shell fallback such as `python3 gate.py || printf '<ask JSON>'` therefore turns a missing script, a missing interpreter, an import error and a crash into an explicit `ask`. It cannot help when Claude Code itself cancels the hook at its timeout, or when hooks are disabled.
- **Startup costs** (this machine): Python 17 ms, standard-library imports 37 ms, `import typesafe_sdk` 130 ms (up to 244). A plain standard-library `urllib` POST to `/v1/systemone` works with the same request shape; five single-shot calls took 226 to 435 ms each because every hook run is a fresh process with a fresh connection. **Realistic per-command overhead is about 0.3 to 0.5 seconds**, more than the 150 ms measured earlier with a warm client. Still far under the 3 second ceiling.
- **Four `python3` executables** are on the PATH: anaconda 3.12.4, the python.org framework build 3.12.3, `/usr/local/bin` 3.14.5, and `/usr/bin` 3.9.6. A hook may not inherit the interactive PATH, and anaconda upgrades can change what `python3` means.
- **SessionStart hooks** run in the background at launch, but Claude's first response waits for them, so a self-check must be fast. Plain stdout goes to the model's context; `systemMessage` is the field for messages to the user. Whether SessionStart delivers `systemMessage` to the user is not stated and needs a test.
- **Matchers are unanchored regular expressions**: `Edit.*` matches `NotebookEdit`, and the prototype's `Bash|mcp__.*` would also match any tool whose name merely contains `Bash`. Anchor with `^` and `$`.
- **File-tool inputs**: `Write`, `Edit` and `Read` give an absolute `tool_input.file_path`. The docs do not name the `NotebookEdit` path field; it must be checked in a test.


## Answer

The user accepted all eight recommendations (Q42 to Q49).

**1. The promise the spec makes (Q42)**: the gate asks whenever it judges a call risky. When it cannot run at all (missing script or interpreter, crash, bad output), it asks anyway through a shell fallback. It cannot help in four situations where Claude Code fails open: the hook is cancelled at its timeout; hooks are disabled (`disableAllHooks` or `--bare`); the settings entry is missing or mistyped; or the shell itself cannot start. It never claims to block anything, and in unattended runs an escalation acts as a denial. The spec lists the four cases plainly.

**2. Supported and unsupported (Q43)**
- **Supported and verified**: headless runs, where an escalation is a denial (default, dontAsk, acceptEdits, bypassPermissions, plan), per [Test the unproven modes](08-test-unproven-modes.md).
- **Supported by documentation only**: interactive default and auto mode; the other interactive modes are unverified.
- **Unsupported**: `--bare`, `disableAllHooks`, and Claude Code older than **2.1.211** (the version that fixed auto mode honoring `ask`). Tested on 2.1.278. The version is recorded in the audit log.
- The user runs the interactive checklist in `mode-tests/README.md` before enforcement; that becomes an exit criterion in [Trial mode and the audit log](12-trial-mode-and-audit-log.md).

**3. The launcher (Q44)**: the hook `command` is a shell fallback around a standard-library-only Python script: `PY gate.py || printf '<ask JSON>'`. The script calls TypeSafe over plain HTTPS (`urllib`) instead of the SDK, catches every error including import errors, and enforces the 3 second deadline itself. Measured on this machine: Python 17 ms, standard-library imports 37 ms versus 130 ms for the SDK; realistic overhead is about 0.3 to 0.5 seconds per judged command (a fresh process and connection each time), not the 150 ms seen with a warm client.

**4. Interpreter (Q45)**: an absolute path to the python.org build, `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3` (3.12.3), not anaconda and not `python3` on the PATH. The script needs no packages, so any Python 3.9 or later works. If the path breaks, the shell fallback asks.

**5. Hook timeout (Q46)**: 5 seconds, above the 3 second internal ceiling, so the script's own `ask` arrives before Claude Code cancels the hook and fails open.

**6. Noticing a silently disabled gate (Q47)**: all three of (a) a SessionStart self-check written as inline shell that does not depend on the gate script, checking that the script is executable, the interpreter runs and the key is readable, and warning through `systemMessage`; (b) a heartbeat entry in the audit log each session, so a gap shows in trial review; (c) a `doctor` command that confirms the settings entry, path and key on demand. The self-check must be fast, since Claude's first response waits for SessionStart hooks.

**7. Tool inputs and matcher (Q48)**: the launcher branches on the tool name. Bash uses the command; MCP tools use the JSON input; Write and Edit use `tool_input.file_path`; NotebookEdit tries `file_path` and then `notebook_path`; any other tool gets no opinion. The matcher is anchored: `^(Bash|Write|Edit|NotebookEdit)$|^mcp__`.

**8. Verified in the real hook runner (Q49)**: three headless runs on 2.1.278 (about $0.02). A healthy gate stayed quiet and the command ran (control). A mistyped script path and a script that exits 1 were each turned into an `ask` by the shell fallback (shown as a denial because nothing can prompt headless). The runs are in `mode-tests/run_wrapper.py`. Scratch transcript litter was removed.

**Still unverified** (the spec lists these as such): whether SessionStart delivers `systemMessage` to the user; NotebookEdit's path field name; the interactive prompt in each mode and auto mode; a mistyped interpreter path (the same fallback mechanism should cover it); the gate being killed part-way through printing.

**Spec deltas from the prototype, collected**: shell fallback command; standard-library launcher instead of the SDK; pinned interpreter; `timeout` 5; anchored matcher covering Write, Edit and NotebookEdit; SessionStart self-check, heartbeat and `doctor`; no `cwd` or description sent to Jev; `deny` removed; six signals at one 0.4 threshold; local pre-check with the always-escalate list; audit log.
