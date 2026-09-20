# Mode tests for ticket 08 (THROWAWAY)

Headless tests of what a PreToolUse hook's `ask` does, using a stub hook that only logs and returns `ask` for the marker command `gate-test`. Harmless `echo` and `mkdir` in scratch folders only; never touches user settings.

    python3 setup.py     # creates scratch folders a (allow rule), b (hook timeout 2 s), c (no allow rule)
    python3 run.py       # ~15 runs of `claude -p` on Haiku, a few cents; `python3 run.py TESTNAME` runs one
    rm -rf a b c runs    # clean up; also delete any ~/.claude/projects/*mode-tests-* folders Claude Code creates

Notes learned the hard way: a project's `permissions.allow` rules are ignored until the workspace is trusted, which `-p` cannot do, so tests that need an allow rule pass it with `--settings <file>` (see `allow.json`). `--no-session-persistence` still left tiny transcript folders under `~/.claude/projects`.

## Interactive checklist (optional, needs a human at a terminal)

    python3 setup.py && cd c && echo ask > hook_mode.txt
    claude --setting-sources project --settings "$PWD/../allow.json" --strict-mcp-config --disable-slash-commands --model haiku

1. Default mode: ask Claude to "run mkdir gate-test-dir". Expect a permission prompt labelled `[settings]` with the reason "stub gate: ask", even though allow.json permits that command. Answer No.
2. Press Shift+Tab to reach acceptEdits and repeat. Expect a prompt.
3. Relaunch with `--permission-mode bypassPermissions --allow-dangerously-skip-permissions` and repeat. Record: prompt, denial, or it runs.
4. If auto mode is available to you, relaunch with `--permission-mode auto` and repeat. Record the same.

## Ticket 07: does a shell fallback turn a broken hook into an `ask`?

    python3 run_wrapper.py   # 3 runs, ~$0.02: healthy gate stays quiet (control), mistyped script path, script exits 1

Result on Claude Code 2.1.278: the control ran the command; the mistyped path and the crash were each turned into an `ask` by `PY gate.py || printf '<ask JSON>'` (shown as a denial because nothing can prompt headless). Not tested: a mistyped interpreter path, and the gate being killed part-way through printing.
