"""The SessionStart self-check and its heartbeat (slice 6 of docs/permission-gate/SPEC.md).

The check is plain POSIX shell placed inline in the hook command, so it does not depend on gate.py, on the interpreter
or on anything else it is checking. Every session start it appends one line to heartbeat.jsonl (a plain file, not
hash-chained) and, when something is wrong, prints a `systemMessage` so the user hears about it. Whether SessionStart
delivers that message to the user is not stated in the documentation and is still to be verified.

This module holds the script text, builds the hook command, and reads heartbeats back for doctor, reconcile and review.
Standard library only, Python 3.9+.
"""
from __future__ import annotations

import json
import os
import shlex
from typing import List, Optional

import audit

SCRIPT = r"""umask 077
PY=__PY__
GATE=__GATE__
H="${JEV_GATE_HOME:-$HOME}"
D="$H/.local/state/jev-gate"
C="$H/.config/jev-gate/config.json"
IN=$(cat 2>/dev/null)
SID=$(printf '%s' "$IN" | sed -n 's/.*"session_id"[ ]*:[ ]*"\([^"]*\)".*/\1/p' | head -n 1 | tr -cd 'A-Za-z0-9_.-')
SRC=$(printf '%s' "$IN" | sed -n 's/.*"source"[ ]*:[ ]*"\([^"]*\)".*/\1/p' | head -n 1 | tr -cd 'A-Za-z0-9_.-')
BAD=""
[ -x "$PY" ] || BAD="$BAD interpreter-missing"
[ -f "$GATE" ] || BAD="$BAD script-missing"
if [ -x "$PY" ]; then "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1 || BAD="$BAD interpreter-broken"; fi
[ -f "$C" ] || BAD="$BAD config-missing"
if [ -z "$TYPESAFE_API_KEY" ]; then
  if [ -n "$JEV_GATE_NO_KEYCHAIN" ] || ! security find-generic-password -s typesafe >/dev/null 2>&1; then BAD="$BAD key-missing"; fi
fi
mkdir -p "$D" 2>/dev/null
OK=true
[ -z "$BAD" ] || OK=false
printf '{"ts":"%s","session":"%s","source":"%s","ok":%s,"problems":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SID" "$SRC" "$OK" "${BAD# }" >> "$D/heartbeat.jsonl" 2>/dev/null
[ -z "$BAD" ] || printf '{"systemMessage":"Jev gate self-check failed (%s). The gate may not be protecting this session; run doctor.py."}' "${BAD# }"
exit 0
"""


def command(python: str, gate: str) -> str:
    """The hook command: the script with the two paths shell-quoted, passed to `sh -c` as one argument."""
    script = SCRIPT.replace("__PY__", shlex.quote(python)).replace("__GATE__", shlex.quote(gate))
    return script


def path(state: str) -> str:
    return os.path.join(state, "heartbeat.jsonl")


def records(state: str, since=None, until=None) -> List[dict]:
    """Readable heartbeats in [since, until), oldest first. Malformed lines are skipped."""
    out = []
    try:
        fh = open(path(state))
    except OSError:
        return out
    with fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            when = audit.parse_ts(rec.get("ts")) if isinstance(rec, dict) else None
            if when is None or (since and when < since) or (until and when >= until):
                continue
            out.append(rec)
    out.sort(key=lambda r: r["ts"])
    return out


def by_session(beats: List[dict]) -> dict:
    """session id -> list of its heartbeats."""
    sessions: dict = {}
    for b in beats:
        sessions.setdefault(str(b.get("session")), []).append(b)
    return sessions


def first_ts(state: str) -> Optional[object]:
    beats = records(state)
    return audit.parse_ts(beats[0]["ts"]) if beats else None
