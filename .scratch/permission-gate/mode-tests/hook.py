#!/usr/bin/env python3
"""THROWAWAY stub hook for ticket 08. Logs every call; returns `ask` only for the marker command."""
import json, os, sys, time
ev = json.load(sys.stdin)
cwd = ev.get("cwd") or os.getcwd()
mode_file = os.path.join(cwd, "hook_mode.txt")
mode = open(mode_file).read().strip() if os.path.exists(mode_file) else "ask"
cmd = str((ev.get("tool_input") or {}).get("command", ""))
with open(os.path.join(cwd, "hook.log"), "a") as fh:
    fh.write(json.dumps({"t": round(time.time(), 1), "permission_mode": ev.get("permission_mode"), "tool": ev.get("tool_name"),
                         "cmd": cmd[:60], "agent_id": ev.get("agent_id"), "agent_type": ev.get("agent_type"), "hook_mode": mode}) + "\n")
if "gate-test" not in cmd or mode == "silent":
    sys.exit(0)
if mode == "sleep":
    time.sleep(6)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                          "permissionDecisionReason": "stub gate: ask"}}))
