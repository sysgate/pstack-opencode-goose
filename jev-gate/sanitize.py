"""What leaves the machine, and what the audit log keeps: redaction and file-name masking.

Standard library only, Python 3.9+. This reproduces exactly the transformation the evaluation applied (redaction of
secret-like strings and emails, then masking of file names under /Volumes, Downloads and Documents), so the text Jev
sees live has the same shape as the text the thresholds were fitted to. It adds one thing the evaluation lacked:
the body of a data heredoc (`cat >> notes.md <<EOF`) is replaced by a one-line marker before sending, which keeps
documentation text off the wire and matches how the local rules treat it.
"""
from __future__ import annotations

import json
import re
from typing import Any

import precheck as p

AUTH_HEADER = re.compile(r"(?i)(authorization:\s*(?:bearer|basic)\s+)\S+")
BEARER = re.compile(r"\b(Bearer\s+)[A-Za-z0-9._\-]{16,}")
LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
HEX_ONLY = re.compile(r"^[0-9a-fA-F]+$")
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

MAX_JEV_CHARS = 2000        # as evaluated
MAX_MCP_VALUE_CHARS = 200   # a message body or document text in an MCP argument must not ride along
PREFIX_CHARS = 80


def redact(text: str) -> str:
    text = p.PEM.sub("<REDACTED:private-key>", text)
    text = p.TOKEN_PREFIXES.sub("<REDACTED:token>", text)
    text = p.JWT.sub("<REDACTED:jwt>", text)
    text = AUTH_HEADER.sub(r"\1<REDACTED>", text)
    text = BEARER.sub(r"\1<REDACTED>", text)
    text = p.URL_CREDS.sub(r"\1<REDACTED>@", text)

    def assign(m):
        if m.group(3).startswith(("$", '"$', "'$")):  # a reference, not a literal
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}<REDACTED>"

    text = p.ASSIGN.sub(assign, text)
    text = p.SECRET_FLAG.sub(r"\1<REDACTED>", text)

    def long_token(m):
        tok = m.group(0)
        if (HEX_ONLY.match(tok) and len(tok) <= 64) or UUID.match(tok):
            return tok  # git SHAs, session ids
        if m.start() > 0 and m.string[m.start() - 1] in "/.":
            return tok  # a path or file-name segment
        if not (re.search(r"\d", tok) and re.search(r"[A-Za-z]", tok)):
            return tok
        return "<REDACTED:long-token>"

    text = LONG_TOKEN.sub(long_token, text)
    return EMAIL.sub("<EMAIL>", text)


PATH = re.compile(
    r"""(?P<q>["'])(?P<qp>[^"']*?(?:/Volumes/|/Downloads/|/Documents/)[^"']*)(?P=q)"""
    r"""|(?P<up>(?:/Volumes/|/Users/[^/\s]+/(?:Downloads|Documents)/)(?:\\.|[^\s\\])+)"""  # honors `My\ Diary.txt`
)


def _mask_path(path: str) -> str:
    if re.match(r"^/Volumes/[^/]+$", path) or "/" not in path:
        return path  # a bare volume name is a folder, not a file
    head, _, tail = path.rpartition("/")
    if not tail:
        return path
    ext = re.search(r"(\.[A-Za-z0-9]{1,5})$", tail)
    return f"{head}/<FILE>{ext.group(1) if ext else ''}"


def mask_paths(text: str) -> str:
    """File names under /Volumes, Downloads and Documents become <FILE>; the folders stay."""
    def sub(m):
        if m.group("qp") is not None:
            return f"{m.group('q')}{_mask_path(m.group('qp'))}{m.group('q')}"
        return _mask_path(m.group("up"))
    return PATH.sub(sub, text)


def sanitize(text: str) -> str:
    return mask_paths(redact(text))


def strip_data_heredocs_marked(text: str) -> str:
    """Like precheck.strip_data_heredocs, but leaves a marker with the omitted length; interpreter heredocs are kept."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = p.HEREDOC.search(line)
        if m and "<<<" not in line:
            marker, j = m.group(1), i + 1
            while j < len(lines) and lines[j].strip() != marker:
                j += 1
            body = lines[i + 1: j]
            if p.INTERPRETER.search(line):
                out.extend(body)
            elif body:
                out.append(f"[heredoc body omitted: {sum(len(b) + 1 for b in body)} chars]")
            if j < len(lines):
                out.append(lines[j])  # the terminator
            i = j
        i += 1
    return "\n".join(out)


def for_jev_bash(command: str) -> str:
    return sanitize(strip_data_heredocs_marked(command))[:MAX_JEV_CHARS]


def _shorten(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= MAX_MCP_VALUE_CHARS else value[:MAX_MCP_VALUE_CHARS] + "…"
    if isinstance(value, dict):
        return {k: _shorten(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_shorten(v) for v in value]
    return value


def for_jev_mcp(tool_input: Any) -> str:
    return sanitize(json.dumps(_shorten(tool_input), sort_keys=True, ensure_ascii=False, default=str))[:MAX_JEV_CHARS]


def prefix(text: str, limit: int = PREFIX_CHARS) -> str:
    """The audit log's excerpt: redacted, masked, whitespace collapsed, cut at `limit` characters."""
    flat = " ".join(sanitize(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"
