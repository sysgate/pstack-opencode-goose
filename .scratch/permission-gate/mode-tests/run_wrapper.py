#!/usr/bin/env python3
"""THROWAWAY (ticket 07): does a shell fallback turn a broken hook into an explicit `ask` in the real hook runner?
Harmless `echo gate-test` only, in folder w, via `claude -p` on Haiku."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run as R
PY = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
ASK = '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"gate failed to run; confirm manually"}}'
def write(cmd):
    cfg = {"hooks": {"PreToolUse": [{"matcher": "^Bash$", "hooks": [{"type": "command", "command": cmd, "timeout": 5}]}]}}
    json.dump(cfg, open(f"{R.S}/w/.claude/settings.json", "w"), indent=2)
TESTS = [
  ("W0_control_healthy_gate_stays_quiet", f"{PY} {R.S}/hook.py || printf '%s' '{ASK}'", "silent"),
  ("W1_mistyped_script_path", f"{PY} /nonexistent/gate.py || printf '%s' '{ASK}'", "silent"),
  ("W2_script_crashes_exit1", f"{PY} {R.S}/crash.py || printf '%s' '{ASK}'", "silent"),
]
for name, cmd, hook_mode in TESTS:
    write(cmd)
    r = R.run(name, "w", hook_mode, "default", "echo gate-test")
    print(f"{name:<40} denials={r['denials']} result={r['result'][:32]!r:<36} hook_calls={r['hook_calls']} cost={r['cost']}")
