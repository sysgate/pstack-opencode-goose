"""Reconcile the audit log with Claude Code's own session transcripts (slice 5 of docs/permission-gate/SPEC.md).

Standard library only, Python 3.9+. A hook that silently stopped running (a mistyped path, a timeout, disabled hooks)
leaves no error, only a gap: the transcript shows N tool calls of the kinds the gate handles, the audit log fewer.
This compares them per session. It reads transcripts only to count tool calls; it never stores or prints their content.
"""
from __future__ import annotations

import collections
import datetime
import glob
import json
import os
from typing import Dict, List, Optional

import audit
import config
import heartbeat

MATCHED = ("Bash", "Write", "Edit", "NotebookEdit")


def is_matched(name: str) -> bool:
    return name in MATCHED or name.startswith("mcp__")


def projects_root() -> str:
    return os.path.join(config.home(), ".claude", "projects")


def scan(root: str, since: Optional[datetime.datetime]) -> Dict[str, dict]:
    """session id -> {counts: Counter of tool names, cwd, first, last}, for tool calls at or after `since`."""
    sessions: Dict[str, dict] = {}
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        try:
            fh = open(path, errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                content = msg.get("content") if isinstance(msg, dict) else None
                if not isinstance(content, list):
                    continue
                when = audit.parse_ts(rec.get("timestamp"))
                for item in content:
                    if not (isinstance(item, dict) and item.get("type") == "tool_use" and is_matched(str(item.get("name", "")))):
                        continue
                    if since and when and when < since:
                        continue
                    sid = rec.get("sessionId") or rec.get("session_id") or os.path.basename(path)
                    s = sessions.setdefault(sid, {"counts": collections.Counter(), "cwd": "", "first": when, "last": when})
                    s["counts"][str(item["name"])] += 1
                    s["cwd"] = s["cwd"] or str(rec.get("cwd") or "")
                    if when:
                        s["first"] = min(s["first"] or when, when)
                        s["last"] = max(s["last"] or when, when)
    return sessions


def reconcile(cfg, since: Optional[datetime.datetime] = None, root: Optional[str] = None) -> dict:
    recs = audit.records(cfg.state_dir)
    if not recs:
        return {"rows": [], "note": "no audit records yet, so there is nothing to reconcile"}
    since = since or audit.parse_ts(recs[0]["ts"])
    logged: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in recs:
        if (audit.parse_ts(r["ts"]) or since) >= since:
            logged[str(r.get("session"))][r.get("tool")] += 1
    expected = scan(root or projects_root(), since)
    beats = heartbeat.records(cfg.state_dir)
    beats_by = heartbeat.by_session(beats)
    first_beat = audit.parse_ts(beats[0]["ts"]) if beats else None
    scoped = bool(cfg.scopes)
    rows: List[dict] = []
    for sid in sorted(set(expected) | set(logged)):
        exp = expected.get(sid)
        n_exp = sum(exp["counts"].values()) if exp else 0
        n_log = sum(logged.get(sid, {}).values())
        cwd = exp["cwd"] if exp else ""
        if exp and scoped and config.scope_for(cwd, cfg) == "unscoped":
            continue  # a session outside the configured scopes was never supposed to have the gate
        gap = n_exp - n_log
        if not exp:
            status, why = "INFO", "logged calls but no transcript (transcripts may have been cleaned up)"
        elif n_log == 0:
            status, why = "FAIL", "no audit records at all: was the gate running in this session?"
        elif gap == 0:
            status, why = "OK", "every matched call was logged"
        elif gap == 1:
            status, why = "WARN", "one call missing (it may have been in flight when the session ended)"
        elif gap > 1:
            status, why = "FAIL", f"{gap} matched calls have no audit record"
        else:
            status, why = "INFO", f"{-gap} more records than transcript calls"
        per_tool = {t: (exp["counts"].get(t, 0) if exp else 0, logged.get(sid, {}).get(t, 0))
                    for t in sorted(set(exp["counts"] if exp else {}) | set(logged.get(sid, {})))}
        # The SessionStart heartbeat: is there one for this session, and did its self-check pass?
        if not exp or not beats:
            hb = "not recorded" if exp else ""
        elif exp["first"] and first_beat and exp["first"] < first_beat:
            hb = "n/a"                                  # the session began before the self-check existed
        elif sid not in beats_by:
            hb = "missing"
        else:
            hb = "ok" if any(b.get("ok") for b in beats_by[sid]) else "failed"
        if hb in ("missing", "failed") and status == "OK":
            status, why = "WARN", f"every matched call was logged, but the session's heartbeat is {hb}"
        rows.append({"session": sid, "scope": config.scope_for(cwd, cfg) if cwd else "?", "expected": n_exp, "logged": n_log,
                     "gap": gap, "status": status, "why": why, "per_tool": per_tool, "heartbeat": hb})
    note = "" if scoped else "no scopes are configured, so every transcript session was compared"
    return {"rows": rows, "since": since.isoformat(), "note": note}


def summary(result: dict) -> dict:
    rows = result["rows"]
    return {"sessions": len(rows), "expected": sum(r["expected"] for r in rows), "logged": sum(r["logged"] for r in rows),
            "fail": sum(r["status"] == "FAIL" for r in rows), "warn": sum(r["status"] == "WARN" for r in rows)}


def format_report(result: dict) -> List[str]:
    if not result["rows"]:
        return [f"INFO  {result.get('note') or 'no sessions to compare'}"]
    lines = [f"since {result['since']}" + (f"  ({result['note']})" if result["note"] else "")]
    for r in result["rows"]:
        hb = f"  heartbeat {r['heartbeat']}" if r.get("heartbeat") else ""
        lines.append(f"{r['status']:<5} {str(r['session'])[:8]}  {r['scope']:<10} transcript {r['expected']:>4}  logged {r['logged']:>4}{hb}  {r['why']}")
    s = summary(result)
    lines.append(f"{'FAIL' if s['fail'] else 'OK':<5} {s['sessions']} sessions: {s['expected']} matched calls in transcripts, {s['logged']} logged, "
                 f"{s['fail']} failing, {s['warn']} warning")
    return lines
