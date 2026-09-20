"""PROTOTYPE (throwaway): the v1 local pre-check from ticket 05, code only, nothing sent anywhere.

Order in the real gate: local pre-check -> fast path -> Jev. This module is the first stage.
Each rule returns a pattern TYPE name, never the matched text (the ask message must not repeat it).
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..")))
import extract_commands as x  # noqa: E402  (token shapes shared with the redactor)
import typesafe_permission_gate as gate  # noqa: E402  (existing fast_path)

# ---- 1. literal secrets ------------------------------------------------------
AUTH_LITERAL = re.compile(r"(?i)authorization:\s*(?:bearer|basic)\s+(?!\$)\S{8,}")
BEARER_LITERAL = re.compile(r"\bBearer\s+(?!\$)[A-Za-z0-9._\-]{16,}")


def literal_secret(text):
    kinds = []
    for name, rx in (("private key block", x.PEM), ("known token prefix", x.TOKEN_PREFIXES), ("jwt", x.JWT),
                     ("auth header", AUTH_LITERAL), ("bearer token", BEARER_LITERAL), ("url credentials", x.URL_CREDS)):
        if rx.search(text):
            kinds.append(name)
    for m in x.ASSIGN.finditer(text):
        if not m.group(3).startswith(("$", '"$', "'$")):
            kinds.append("secret-named assignment")
            break
    if x.SECRET_FLAG.search(text):
        kinds.append("secret flag with literal value")
    return sorted(set(kinds))


# ---- 2. commands that print secrets ------------------------------------------
READERS = r"(?:cat|head|tail|less|more|cp|scp|strings|xxd|base64|bat|source)"
SECRET_PRINTING = [
    ("keychain read", re.compile(r"\bsecurity\s+(?:find-(?:generic|internet)-password\b[^\n;|&]*\s-w\b|dump-keychain)")),
    ("private key read", re.compile(rf"\b{READERS}\b[^\n;|&]*(?:~|\$HOME|/Users/[^/\s]+)/\.ssh/(?!config\b|known_hosts\b|authorized_keys\b)(?!\S*\.pub\b)\S+")),
    ("pem read", re.compile(rf"\b{READERS}\b[^\n;|&]*\.pem\b")),
    ("gpg secret export", re.compile(r"\bgpg\b[^\n;|&]*--export-secret-(?:keys|subkeys)\b")),
    ("environment dump", re.compile(r"(?:^|[;&]\s*|\n)\s*(?:printenv|env)\s*(?:$|[;&\n])")),
    (".env contents", re.compile(rf"(?:\b{READERS}\b|(?<![\w])\.\s)[^\n;|&]*(?<![\w.])\.env(?![\w])(?!\.(?:example|sample|template))|curl\b[^\n]*-d\s*@\S*\.env\b")),
]


def secret_printing(text):
    return sorted({name for name, rx in SECRET_PRINTING if rx.search(text)})


# ---- 3. destructive and irreversible ------------------------------------------
BROAD = {"/", "~", "~/", "$HOME", "$HOME/", "${HOME}", "/Users", "/*", "~/*", "$HOME/*", "*", ".", "./", "..", "../", "./*"}
RM = re.compile(r"\brm\s+((?:-[A-Za-z]+\s+|--[a-z\-]+\s+)+)([^;&|\n]+)")
FORCE_PUSH = re.compile(r"\bgit\s+push\b[^\n;|&]*(?:--force\b|--force-with-lease\b|\s-f\b|\s\+\S)")
PIPE_SHELL = re.compile(r"\|\s*(?:sudo\s+)?(?:ba|z|da|fi)?sh\b(?![\w-])|\b(?:ba|z)?sh\s+<\(|\bsource\s+<\(|\beval\s+\"?\$\(\s*(?:curl|wget)")


def destructive_seed(text):
    kinds = []
    if re.search(r"\bsudo\b", text):
        kinds.append("sudo")
    for m in RM.finditer(text):
        if not re.search(r"-[A-Za-z]*[rRf]|--recursive|--force", m.group(1)):
            continue
        for tok in m.group(2).split():
            t = tok.strip("'\"").rstrip("/") if tok.strip("'\"") not in ("/", "~/", "$HOME/") else tok.strip("'\"")
            if t in BROAD or re.fullmatch(r"/Users/[^/]+", t):
                kinds.append("rm on home, root or whole directory")
    if FORCE_PUSH.search(text):
        kinds.append("force push")
    if PIPE_SHELL.search(text):
        kinds.append("pipe to shell")
    return sorted(set(kinds))


# ---- 4. protected paths (write TARGET, not mention) ----------------------------
PROTECTED = [
    ("agent configuration", re.compile(r"(?:^|[/\s\"'=~$])\.claude(?:\.json)?(?:/|$|[\s\"'])")),
    ("MCP configuration", re.compile(r"(?:^|/)\.mcp\.json\b")),
    ("shell profile", re.compile(r"(?:^|/)\.(?:zshrc|zprofile|zshenv|bashrc|bash_profile|profile)(?![\w.])")),
    ("scheduled jobs", re.compile(r"LaunchAgents/|LaunchDaemons/|/var/spool/cron|/etc/cron")),
    ("system configuration", re.compile(r"(?<![\w.~])/etc/")),
    ("ssh configuration", re.compile(r"\.ssh/(?:config|authorized_keys)\b")),
    ("the gate's own files", re.compile(r"typesafe_permission_gate|permission_gate")),
]
SCHED_COMMAND = re.compile(r"\bcrontab\s+(?:-e\b|-\s*$|-\s*[;&|]|[^\s-]\S*)|\blaunchctl\s+(?:load|bootstrap|enable|submit)\b|(?:\|\s*)crontab\s+-")
WRITERS = {"tee", "mv", "cp", "rm", "rmdir", "ln", "install", "chmod", "chown", "chgrp", "truncate", "touch", "unlink"}
REDIRECT = re.compile(r"(?<![<>&\d])\d?>>?\|?\s*([^\s;|&<>]+)")
PY_WRITE = re.compile(r"open\([^)]*,\s*['\"][wa][b+]?['\"]|\.write_text\(|\.write_bytes\(|shutil\.(?:copy|move)")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")


def strip_data_heredocs(text):
    """Drop the body of heredocs that only feed data to cat/tee; keep interpreter heredocs."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = HEREDOC.search(line)
        if m and not re.search(r"<<<", line):
            marker, first = m.group(1), line.strip().split()[:1]
            interpreter = re.search(r"\b(?:python3?|node|bash|sh|zsh|perl|ruby)\b", line) is not None
            j = i + 1
            while j < len(lines) and lines[j].strip() != marker:
                j += 1
            if not interpreter:
                i = j  # skip the body, keep going after the terminator
            else:
                out.extend(lines[i + 1: j])
                i = j
        i += 1
    return "\n".join(out)


def _statements(text):
    return [s for s in re.split(r";|&&|\|\||\||\n", text) if s.strip()]


def _tokens(stmt):
    return [t.strip("'\"") for t in re.findall(r"\"[^\"]*\"|'[^']*'|\S+", stmt)]


def write_targets(stmt):
    targets = [m.group(1).strip("'\"") for m in REDIRECT.finditer(stmt)]
    toks = _tokens(stmt)
    while toks and (toks[0] in ("sudo", "command", "env", "nohup") or re.fullmatch(r"\w+=\S*", toks[0])):
        toks = toks[1:]
    if toks:
        verb, args = os.path.basename(toks[0]), [t for t in toks[1:] if not t.startswith("-")]
        if verb in ("cp", "ln", "install"):
            targets += args[-1:]  # only the destination is written; copying FROM a protected file is a read
        elif verb in WRITERS:
            targets += args
        elif verb == "sed" and any(t.startswith("-i") for t in toks[1:]):
            targets += args[1:]
    return targets


def protected_write(text):
    """Bash: a write whose target is a protected path. Returns protected-area names."""
    kinds, body = set(), strip_data_heredocs(text)
    for stmt in _statements(body):
        for target in write_targets(stmt):
            for name, rx in PROTECTED:
                if rx.search(target):
                    kinds.add(name)
        if PY_WRITE.search(stmt):
            for name, rx in PROTECTED:
                if rx.search(stmt):
                    kinds.add(name)
    if SCHED_COMMAND.search(body):
        kinds.add("scheduled jobs")
    return sorted(kinds)


def protected_file_path(file_path):
    """Write, Edit, NotebookEdit: the path itself is the target (absolute and ~-expanded by Claude Code)."""
    return sorted({name for name, rx in PROTECTED if rx.search(file_path)})


# ---- 5. agent-configuration CLI commands (added by decision Q40 in ticket 06) ---------
AGENT_CLI = re.compile(r"\bclaude\s+(?:plugin\s+(?:install|marketplace\s+add|add)|mcp\s+add)\b")


def agent_cli(text):
    return ["adds a plugin, marketplace or MCP server"] if AGENT_CLI.search(text) else []


# ---- the whole stage ------------------------------------------------------------
def precheck(tool, text):
    """Returns (rule family, [pattern types]) if the local pre-check escalates, else None."""
    if tool == "Bash":
        # Data heredocs (cat >> notes.md <<EOF ...) are text, not commands: only the literal-secret rule reads them.
        body = strip_data_heredocs(text)
        for family, fn, src in (("literal secret", literal_secret, text), ("prints secrets", secret_printing, body),
                                ("destructive seed", destructive_seed, body), ("protected write", protected_write, text),
                                ("agent configuration command", agent_cli, body)):
            kinds = fn(src)
            if kinds:
                return family, kinds
    elif tool in ("Write", "Edit", "NotebookEdit"):
        kinds = protected_file_path(text)
        if kinds:
            return "protected write", kinds
    return None


def is_fast_path(tool, text):
    return gate.fast_path({"tool_name": tool, "tool_input": {"command": text}})
