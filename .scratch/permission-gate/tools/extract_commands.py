#!/usr/bin/env python3
"""Ticket 03: build the local, redacted pool of candidate commands.

Reads Bash and mcp__* tool calls from Claude Code transcripts in exactly two
project folders (never Documents-Memory), redacts secret-like strings, de-duplicates,
and writes .scratch/permission-gate/data/candidates.jsonl (owner-only permissions).

Nothing leaves this machine. This script prints COUNTS ONLY, never command text.
The 'heuristic signals' are a rough feasibility count, not labels: labeling is
ticket 04 and is done by a human.
"""

import collections
import glob
import hashlib
import json
import os
import re
import stat

ROOT = os.path.expanduser("~/.claude/projects")
ALLOWED_DIRS = ["-Users-robertlai-Projects", "-Users-robertlai-Projects-chi"]
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
MAX_BASH_CHARS = 2000
MAX_MCP_CHARS = 300

# ---- redaction --------------------------------------------------------------
PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)
TOKEN_PREFIXES = re.compile(
    r"\b(?:sk-ant-[A-Za-z0-9_\-]{16,}|sk-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_\-]{30,}|ya29\.[0-9A-Za-z_\-]+)"
)
JWT = re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")
AUTH_HEADER = re.compile(r"(?i)(authorization:\s*(?:bearer|basic)\s+)\S+")
BEARER = re.compile(r"\b(Bearer\s+)[A-Za-z0-9._\-]{16,}")
URL_CREDS = re.compile(r"(://)[^/\s:@]+:[^/\s@]+@")
ASSIGN = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE)[A-Z0-9_]*)"
    r"(\s*=\s*)(\"[^\"]*\"|'[^']*'|[^\s;&|]+)"
)
SECRET_FLAG = re.compile(r"(?i)((?<![A-Za-z0-9])--?(?:password|passwd|token|secret|api[-_]?key)[= ]+)(?!\$)\S+")
LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
HEX_ONLY = re.compile(r"^[0-9a-fA-F]+$")
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def redact(text: str):
    """Returns (redacted_text, secret_hits). Emails are masked but not counted as secrets."""
    hits = 0

    def sub(pattern, repl, s):
        nonlocal hits
        s, n = pattern.subn(repl, s)
        hits += n
        return s

    text = sub(PEM, "<REDACTED:private-key>", text)
    text = sub(TOKEN_PREFIXES, "<REDACTED:token>", text)
    text = sub(JWT, "<REDACTED:jwt>", text)
    text = sub(AUTH_HEADER, r"\1<REDACTED>", text)
    text = sub(BEARER, r"\1<REDACTED>", text)
    text = sub(URL_CREDS, r"\1<REDACTED>@", text)

    def assign(m):
        nonlocal hits
        value = m.group(3)
        if value.startswith(("$", '"$', "'$")):  # a reference, not a literal secret
            return m.group(0)
        hits += 1
        return f"{m.group(1)}{m.group(2)}<REDACTED>"

    text = ASSIGN.sub(assign, text)
    text = sub(SECRET_FLAG, r"\1<REDACTED>", text)

    def long_token(m):
        nonlocal hits
        tok = m.group(0)
        if HEX_ONLY.match(tok) and len(tok) <= 64:  # git SHAs and similar
            return tok
        if UUID.match(tok):  # session and request ids
            return tok
        if m.start() > 0 and m.string[m.start() - 1] in "/.":  # a path or file-name segment
            return tok
        if not (re.search(r"\d", tok) and re.search(r"[A-Za-z]", tok)):
            return tok
        hits += 1
        return "<REDACTED:long-token>"

    text = LONG_TOKEN.sub(long_token, text)
    text = EMAIL.sub("<EMAIL>", text)
    return text, hits


# ---- rough feasibility heuristics (NOT labels) ------------------------------
HEURISTICS = {
    "destructive": re.compile(
        r"\brm\s+-[a-zA-Z]*[rf]|\brm\s+--(?:recursive|force)|\bgit\s+(?:reset\s+--hard|clean\s+-[a-z]*f|checkout\s+--|branch\s+-D)"
        r"|\bdd\s+if=|\bmkfs|\bchmod\s+-R|\bchown\s+-R|\bshred\b|\btruncate\b|DROP\s+TABLE|\bkillall\b|\bpkill\b"
    ),
    "external_effect": re.compile(
        r"\bgit\s+push\b|\bnpm\s+publish|\bgh\s+(?:pr|issue|release|repo)\s+(?:create|merge|close|delete|comment)"
        r"|\bcurl\b[^|]*-X\s*(?:POST|PUT|DELETE|PATCH)|\bdocker\s+push|\bkubectl\s+(?:apply|delete)"
        r"|place_order|cancel_order|send_email|create_draft|share_file|trash_",
        re.I,
    ),
    "reads_secrets": re.compile(
        r"\.ssh/|\.env\b|security\s+find-|\bprintenv\b|\benv\s*(?:$|\|)|id_rsa|\.aws/credentials|\.netrc|keychain"
        r"|\$\{?[A-Z_]*(?:KEY|TOKEN|SECRET|PASSWORD)",
        re.I,
    ),
    "uploads_data": re.compile(
        r"\bcurl\b[^|]*(?:\s-d\s|--data|\s-F\s|--upload-file|\s-T\s)|\bscp\b|\brsync\b[^|]*:|\bgh\s+gist\s+create|\bnc\s"
    ),
    "runs_downloaded": re.compile(
        r"\bcurl\b[^|]*\|\s*(?:ba|z)?sh|\bpip3?\s+install|\bnpm\s+(?:i|install)\b|\bnpx\b|\bbrew\s+install|\bgo\s+install"
        r"|\bpython3?\s+-c[^|]*(?:urlopen|requests\.get)"
    ),
    "tampers_config": re.compile(
        r"\.claude/settings|\.zshrc|\.bashrc|\.zprofile|\.bash_profile|\bcrontab\b|\blaunchctl\b|LaunchAgents|/etc/|\bsudo\b|\.mcp\.json"
    ),
}


def heuristic_signals(kind: str, tool: str, text: str):
    haystack = f"{tool} {text}" if kind == "mcp" else text
    return sorted(name for name, rx in HEURISTICS.items() if rx.search(haystack))


# ---- extraction -------------------------------------------------------------
def transcript_files():
    files = []
    for d in ALLOWED_DIRS:
        base = os.path.join(ROOT, d)
        assert os.path.dirname(base) == ROOT and "Memory" not in d, f"refusing folder {d}"
        files += [(d, f) for f in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True)]
    return files


def main():
    os.umask(0o077)
    os.makedirs(DATA, mode=0o700, exist_ok=True)
    os.chmod(DATA, 0o700)

    pool = {}  # key -> row
    raw_calls = collections.Counter()
    per_folder = collections.Counter()
    sessions = set()
    files = transcript_files()
    stamps = []

    for folder, path in files:
        with open(path, errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                content = msg.get("content") if isinstance(msg, dict) else None
                if not isinstance(content, list):
                    continue
                for item in content:
                    if not (isinstance(item, dict) and item.get("type") == "tool_use"):
                        continue
                    tool = str(item.get("name", ""))
                    inp = item.get("input") if isinstance(item.get("input"), dict) else {}
                    if tool == "Bash":
                        kind, body = "bash", str(inp.get("command", ""))
                    elif tool.startswith("mcp__"):
                        kind, body = "mcp", json.dumps(inp, sort_keys=True, ensure_ascii=False, default=str)
                    else:
                        continue
                    if not body.strip():
                        continue
                    raw_calls[kind] += 1
                    per_folder[folder] += 1
                    limit = MAX_BASH_CHARS if kind == "bash" else MAX_MCP_CHARS
                    text, hits = redact(body[:limit * 2])
                    text = text[:limit]
                    norm = " ".join(text.split())
                    key = hashlib.sha1(f"{kind}|{tool}|{norm}".encode()).hexdigest()[:12]
                    ts = rec.get("timestamp")
                    sid = rec.get("sessionId") or rec.get("session_id")
                    if sid:
                        sessions.add(sid)
                    if ts:
                        stamps.append(ts)
                    row = pool.get(key)
                    if row is None:
                        row = pool[key] = {
                            "id": key, "kind": kind, "tool": tool, "text": text,
                            "description": str(inp.get("description", ""))[:200] if kind == "bash" else "",
                            "cwd": rec.get("cwd", ""), "folder": folder, "count": 0,
                            "first_seen": ts, "last_seen": ts, "sidechain": False,
                            "secret_hit": hits > 0, "redaction_hits": hits,
                            "heuristic_signals": heuristic_signals(kind, tool, text),
                        }
                    row["count"] += 1
                    if ts and (row["first_seen"] is None or ts < row["first_seen"]):
                        row["first_seen"] = ts
                    if ts and (row["last_seen"] is None or ts > row["last_seen"]):
                        row["last_seen"] = ts
                    if rec.get("isSidechain"):
                        row["sidechain"] = True

    out = os.path.join(DATA, "candidates.jsonl")
    with open(out, "w") as fh:
        for row in sorted(pool.values(), key=lambda r: (r["kind"], r["tool"], r["id"])):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.chmod(out, 0o600)

    rows = list(pool.values())
    by_signal = collections.Counter(s for r in rows if not r["secret_hit"] for s in r["heuristic_signals"])
    usable = [r for r in rows if not r["secret_hit"]]
    flagged = [r for r in usable if r["heuristic_signals"]]
    summary = {
        "transcript_files": len(files),
        "sessions": len(sessions),
        "date_range": [min(stamps) if stamps else None, max(stamps) if stamps else None],
        "raw_calls": dict(raw_calls),
        "raw_calls_by_folder": dict(per_folder),
        "unique_candidates": len(rows),
        "unique_by_kind": dict(collections.Counter(r["kind"] for r in rows)),
        "unique_mcp_tools": len({r["tool"] for r in rows if r["kind"] == "mcp"}),
        "secret_hit_candidates": sum(r["secret_hit"] for r in rows),
        "usable_for_evaluation": len(usable),
        "usable_with_heuristic_signal": len(flagged),
        "usable_heuristic_signal_breakdown": dict(by_signal),
        "sidechain_candidates": sum(r["sidechain"] for r in rows),
        "output_file_mode": oct(stat.S_IMODE(os.stat(out).st_mode)),
        "data_dir_mode": oct(stat.S_IMODE(os.stat(DATA).st_mode)),
    }
    with open(os.path.join(DATA, "extract_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    os.chmod(os.path.join(DATA, "extract_summary.json"), 0o600)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
