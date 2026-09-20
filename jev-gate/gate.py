#!/usr/bin/env python3
"""The Jev permission gate: a Claude Code PreToolUse hook (slices 1 to 4 of docs/permission-gate/SPEC.md).

Standard library only, Python 3.9+. Reads the hook event on stdin and prints either nothing (no opinion) or an `ask`
decision. It never prints `allow` or `deny` and never exits with code 2 (ADR 0001).

Flow for a matched call: local pre-check -> fast path -> Jev (one call, six questions, escalate when any signal reaches
the threshold). Every matched call is recorded in the hash-chained audit log.

Modes (config.json): `trial` records what the gate WOULD have done and never prints anything; `enforce` prints the ask.
A missing, invalid or insecure config, bad input, any error and the 3 second deadline all fail closed to an ask (the
one exception: in trial mode a failure is recorded, not shown). NOT built yet: the SessionStart self-check and
heartbeat (slice 6), the review page and reconcile (slice 5).

Register it as a shell-form hook so a broken script still asks (see doctor.py --print-entry):
    PY gate.py || printf '<ask JSON>'
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import signal
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

DEADLINE_SECONDS = 3.0
HOOK_EVENT = "PreToolUse"
HOOK_VERSION = "0.4.0"
FILE_TOOLS = ("Write", "Edit", "NotebookEdit")
T = TypeVar("T")


class DeadlineExceeded(Exception):
    pass


@dataclass
class Outcome:
    tool: str
    raw: str                            # the command, the file path, or the MCP JSON (never printed or logged in full)
    reason: Optional[str] = None        # the ask text, or None for no opinion
    decider: str = "precheck"           # precheck | fast_path | skip | jev | fallback
    family: str = ""                    # local rule family when the pre-check decided
    signals: Optional[dict] = None
    jev_ms: Optional[int] = None
    error: Optional[str] = None         # exception type name when the gate fell back; never a message


def ask_decision(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": HOOK_EVENT, "permissionDecision": "ask", "permissionDecisionReason": reason}}


def run_with_deadline(fn: Callable[[], T], seconds: float) -> T:
    """Run fn, raising DeadlineExceeded if it takes longer. Main thread, POSIX only."""
    def on_alarm(signum, frame):  # noqa: ARG001
        raise DeadlineExceeded()

    previous = signal.signal(signal.SIGALRM, on_alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def is_matched(tool: str) -> bool:
    return tool == "Bash" or tool in FILE_TOOLS or tool.startswith("mcp__")


def extract(event: dict):
    """(tool, raw text) for a call the gate handles, else (tool, None)."""
    tool = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input") or {}
    if tool == "Bash":
        return tool, str(tool_input.get("command", ""))
    if tool in ("Write", "Edit"):
        return tool, str(tool_input.get("file_path", ""))
    if tool == "NotebookEdit":
        return tool, str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")  # verified 2026-09-19: the field is notebook_path
    if tool.startswith("mcp__"):
        return tool, json.dumps(tool_input, sort_keys=True, ensure_ascii=False, default=str)
    return tool, None


def evaluate(event: dict, cfg) -> Optional[Outcome]:
    """The decision for one event, or None when it is not a call the gate handles. Imports lazily so an import
    failure is caught by main() and turned into an ask."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import precheck

    if event.get("hook_event_name", HOOK_EVENT) != HOOK_EVENT:
        return None
    tool, raw = extract(event)
    if raw is None:
        return None
    outcome = Outcome(tool=tool, raw=raw)
    hit = precheck.precheck(tool, raw)                    # 1. local rules; a hit is never sent anywhere
    if hit:
        outcome.reason, outcome.family = precheck.reason(*hit), hit[0]
        return outcome
    if tool in FILE_TOOLS:
        return outcome                                    # Write, Edit and NotebookEdit get the local check only
    if tool == "Bash" and precheck.fast_path(raw):
        outcome.decider = "fast_path"                     # 2. provably local and read-only: no opinion, never allow
        return outcome
    if tool in cfg.skip_list:
        outcome.decider = "skip"
        return outcome
    import jev, questions, sanitize                       # 3. Jev, for Bash and MCP calls
    text = sanitize.for_jev_bash(raw) if tool == "Bash" else sanitize.for_jev_mcp(event.get("tool_input") or {})
    started = time.perf_counter()
    probs = jev.judge(tool, text)
    outcome.decider, outcome.signals = "jev", probs
    outcome.jev_ms = round((time.perf_counter() - started) * 1000)
    flagged = sorted(((s, p) for s, p in probs.items() if p >= cfg.threshold), key=lambda sp: -sp[1])
    if flagged:
        outcome.reason = "Jev gate: " + ", ".join(f"{questions.LABELS[s]} {p:.2f}" for s, p in flagged)
    return outcome


def decide(event: dict) -> Optional[str]:
    """The reason to ask under the default config, or None. Kept for callers that only need the verdict text."""
    import config
    outcome = evaluate(event, config.Config(mode="enforce"))
    return outcome.reason if outcome else None


def build_record(event: dict, outcome: Outcome, cfg, elapsed_ms: int) -> dict:
    import config, precheck, sanitize
    secret_types = precheck.literal_secret(outcome.raw) if outcome.tool == "Bash" else []
    verdict = "no_opinion" if not outcome.reason else ("asked" if cfg.mode == "enforce" else "would_ask")
    return {
        "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.datetime.now().microsecond // 1000:03d}Z",
        "session": event.get("session_id"),
        "scope": config.scope_for(str(event.get("cwd") or ""), cfg),
        "tool": outcome.tool,
        "prefix": None if secret_types else sanitize.prefix(outcome.raw),   # a secret hit logs only its pattern type
        "secret_types": secret_types or None,
        "hash": hashlib.sha256((cfg.salt + "\0" + outcome.raw).encode()).hexdigest(),
        "signals": {s: round(v, 3) for s, v in outcome.signals.items()} if outcome.signals else None,
        "verdict": verdict,
        "decider": outcome.decider,
        "rule_family": outcome.family or None,
        "latency_ms": elapsed_ms,
        "jev_ms": outcome.jev_ms,
        "error": outcome.error,
        "mode": cfg.mode,
        "permission_mode": event.get("permission_mode"),
        "subagent": bool(event.get("agent_id")),
        "wording": cfg.wording,
        "threshold": cfg.threshold,
        "hook": HOOK_VERSION,
        "claude_code": config.claude_version(cfg.state_dir) or None,
    }


def main(stdin=None, stdout=None, stderr=None) -> int:
    out, err = stdout or sys.stdout, stderr or sys.stderr
    started = time.perf_counter()
    event, cfg, outcome, error = None, None, None, None
    try:
        event = json.load(stdin or sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("input is not an object")
        import config
        cfg = config.load()
        outcome = run_with_deadline(lambda: evaluate(event, cfg), DEADLINE_SECONDS)
    except Exception as exc:  # fail closed. Only the exception TYPE is shown: a message could hold command text.
        error = type(exc).__name__
    if error:
        reason = f"Jev gate could not decide ({error}); confirm manually."
        tool, raw = extract(event) if isinstance(event, dict) else ("", None)
        if isinstance(event, dict) and is_matched(tool) and raw is not None:
            outcome = Outcome(tool=tool, raw=raw, reason=reason, decider="fallback", error=error)
        else:
            outcome = Outcome(tool=tool, raw="", reason=reason, decider="fallback")
            outcome.tool = ""  # nothing to record for an event the gate could not even read
    show = bool(outcome and outcome.reason) and (cfg is None or cfg.mode == "enforce")
    if show:
        out.write(json.dumps(ask_decision(outcome.reason)))
        out.flush()
    if cfg is not None and outcome is not None and is_matched(outcome.tool):
        try:
            import audit
            audit.append(cfg.state_dir, build_record(event, outcome, cfg, round((time.perf_counter() - started) * 1000)))
        except Exception as exc:  # the verdict stands; a gap will show in reconciliation
            err.write(f"jev-gate: audit log unavailable ({type(exc).__name__})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
