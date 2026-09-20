#!/usr/bin/env python3
"""SUPERSEDED PROTOTYPE. DO NOT REGISTER. The maintained gate is chi/jev-gate/ (gate.py).

Kept for reference and for the evaluation tools under .scratch/permission-gate/, which import it.
Known defects, all fixed in jev-gate (see docs/permission-gate/SPEC.md section 9): commands are cut at
2000 characters, so padding hides the dangerous tail; a missing typesafe_sdk crashes the hook with exit
1, which Claude Code lets through; the timeout budget can exceed the hook timeout; NaN probabilities
give "no opinion"; fast_path accepts commands that are not read-only (git diff --output=FILE,
git branch -D); it can emit "deny" (jev-gate only ever asks); cwd and description are sent unsanitized.

Original description: Claude Code PreToolUse hook: Jev flags risky Bash commands and MCP tool calls.

Design rules (CHI doctrine: generation proposes, governance admits):
  * Jev can only ESCALATE. This hook never returns "allow", so a wrong or
    manipulated judgment can at worst cause an extra prompt, never skip one.
  * Anything that goes wrong (no key, timeout, bad JSON, crash) returns "ask".
    Claude Code treats exit code 1 as non-blocking and proceeds, so every error
    is caught and turned into an explicit "ask" instead of exiting non-zero.
  * Policy lives in code: Jev only supplies four yes/no probabilities.

It judges commands; it never runs them.

Not installed anywhere, and the registration snippet that used to be here was removed on purpose.

Key: TYPESAFE_API_KEY in the environment, else macOS Keychain service "typesafe".
Data sent to TypeSafe per judged call: tool name, cwd, and the command / tool
input (truncated). Fast-path commands are never sent.
"""

import json
import os
import re
import subprocess
import sys
from typing import Callable, Optional

from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

KEYCHAIN_SERVICE = "typesafe"
ASK_MIN = 0.30  # any signal at or above this forces a prompt (untuned, deliberately low)
DENY_MIN = 0.85  # secrets AND data-out both at or above this -> deny
MAX_INPUT_CHARS = 2000
REQUEST_TIMEOUT_S = 12.0

# Simple, provably local commands skip Jev entirely (no cost, no data sent).
# No opinion is returned, so Claude Code's normal permission flow still applies.
_SHELL_META = re.compile(r"[;|&<>$`()\n\\]")
_FAST_PATH_PREFIXES = (
    "ls", "pwd", "whoami", "date", "wc", "which",
    "git status", "git diff", "git log", "git show", "git branch",
)

QUESTIONS = {
    "destructive": Noul(
        instructions=(
            "Would this tool call delete, overwrite, or irreversibly change files, "
            "data, or system settings, beyond routine regenerable build or test artifacts?"
        )
    ),
    "external_effect": Noul(
        instructions=(
            "Would this tool call change state outside this machine or spend money, "
            "for example pushing or force-pushing code, deploying, sending a message, "
            "placing a trade or order, or writing to a production service?"
        )
    ),
    "reads_secrets": Noul(
        instructions=(
            "Would this tool call read or print credentials, tokens, API keys, "
            "private keys, or password-manager or keychain contents?"
        )
    ),
    "sends_data_out": Noul(
        instructions=(
            "Would this tool call send local files or data to a remote host, or "
            "download and execute code from a remote host?"
        )
    ),
}

Asker = Callable[[dict], dict]  # event -> {question name: probability}


def load_api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY", "")
    if key:
        return key
    try:
        key = subprocess.check_output(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
             "-s", KEYCHAIN_SERVICE, "-w"],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
    except (subprocess.SubprocessError, OSError):
        key = ""
    if not key:
        raise RuntimeError("no TYPESAFE_API_KEY in environment or Keychain")
    return key


def fast_path(event: dict) -> bool:
    """True for simple read-only shell commands that need no judgment."""
    if event.get("tool_name") != "Bash":
        return False
    command = str((event.get("tool_input") or {}).get("command", "")).strip()
    if not command or _SHELL_META.search(command):
        return False
    return any(command == p or command.startswith(p + " ") for p in _FAST_PATH_PREFIXES)


def build_state(event: dict) -> dict:
    tool_input = event.get("tool_input") or {}
    if event.get("tool_name") == "Bash":
        body = str(tool_input.get("command", ""))
    else:
        body = json.dumps(tool_input, ensure_ascii=False, default=str)
    return {
        "tool": event.get("tool_name", ""),
        "cwd": event.get("cwd", ""),
        "description": str(tool_input.get("description", ""))[:300],
        "input": body[:MAX_INPUT_CHARS],
    }


def ask_jev(event: dict) -> dict:
    """One Jev request with all four questions; returns their probabilities."""
    client = TypeSafeClient(
        api_key=load_api_key(),
        retry=RetryPolicy(max_retries=1, timeout=REQUEST_TIMEOUT_S),
        timeout=REQUEST_TIMEOUT_S,
    )
    with client:
        response = client.system_one(state=build_state(event), questions=QUESTIONS)
    return {name: float(response.nouls[name].noul) for name in QUESTIONS}


def decide(probs: dict) -> Optional[tuple]:
    """Policy in code. Returns ("ask"|"deny", reason) or None for no opinion."""
    if probs["reads_secrets"] >= DENY_MIN and probs["sends_data_out"] >= DENY_MIN:
        return ("deny", "Blocked by Jev permission gate: looks like reading secrets and sending them out.")
    flagged = sorted(
        ((name, p) for name, p in probs.items() if p >= ASK_MIN), key=lambda kv: -kv[1]
    )
    if flagged:
        detail = ", ".join(f"{name} {p:.2f}" for name, p in flagged)
        return ("ask", f"Jev permission gate flagged: {detail}")
    return None


def evaluate(event: dict, asker: Asker = ask_jev) -> Optional[tuple]:
    name = str(event.get("tool_name", ""))
    if not (name == "Bash" or name.startswith("mcp__")):
        return None
    if fast_path(event):
        return None
    return decide(asker(event))


def emit(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}))


def main(asker: Asker = ask_jev) -> int:
    try:
        verdict = evaluate(json.load(sys.stdin), asker)
    except Exception as exc:  # fail closed: exit 1 would let the call through
        verdict = ("ask", f"Jev permission gate unavailable ({type(exc).__name__}: {exc}); confirm manually.")
    if verdict:
        emit(*verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
