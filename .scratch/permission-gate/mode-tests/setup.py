#!/usr/bin/env python3
"""THROWAWAY: create the three scratch folders (a: allow rule, b: hook timeout 2 s, c: no allow rule) next to this file."""
import json, os
S = os.path.dirname(os.path.abspath(__file__))
def settings(d, allow, timeout):
    os.makedirs(f"{S}/{d}/.claude", exist_ok=True)
    cfg = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": f"python3 {S}/hook.py", "timeout": timeout}]}]}}
    if allow:
        cfg["permissions"] = {"allow": ["Bash(echo gate-test)", "Bash(mkdir gate-test-dir)"]}
    json.dump(cfg, open(f"{S}/{d}/.claude/settings.json", "w"), indent=2)
settings("a", True, 10); settings("b", True, 2); settings("c", False, 10)
print("created a, b, c under", S)
