"""The local pre-check: code-only rules that run before anything else (slice 2 of docs/permission-gate/SPEC.md).

Standard library only, Python 3.9+. Nothing here touches the network or the disk.

Every rule returns pattern TYPE names, never matched text, so an `ask` reason can never leak a secret
that a command contained. Order in the gate: pre-check -> fast path -> Jev.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

# ---- 1. literal secrets (escalate; nothing is sent anywhere) ------------------------------------
PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)
TOKEN_PREFIXES = re.compile(
    r"\b(?:sk-ant-[A-Za-z0-9_\-]{16,}|sk-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_\-]{30,}|ya29\.[0-9A-Za-z_\-]+)"
)
JWT = re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")
AUTH_LITERAL = re.compile(r"(?i)authorization:\s*(?:bearer|basic)\s+(?!\$)\S{8,}")
BEARER_LITERAL = re.compile(r"\bBearer\s+(?!\$)[A-Za-z0-9._\-]{16,}")
URL_CREDS = re.compile(r"(://)[^/\s:@]+:[^/\s@]+@")
ASSIGN = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE)[A-Z0-9_]*)"
    r"(\s*=\s*)(\"[^\"]*\"|'[^']*'|[^\s;&|]+)"
)
UUID_VALUE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
# The lookbehind keeps `security find-generic-password -s x` from looking like a `-password` flag.
SECRET_FLAG = re.compile(r"(?i)((?<![A-Za-z0-9])--?(?:password|passwd|token|secret|api[-_]?key)[= ]+)(?!\$)\S+")
# Deliberately absent: a generic "long random-looking string" rule. It fires on UUIDs and identifiers,
# so it may redact but never escalates on its own.


def looks_like_secret_value(value: str) -> bool:
    """Whether the right-hand side of a secret-named assignment reads as a literal secret rather than code or a setting.
    Not a secret: a reference or expression (`$X`, `$(...)`, a call, an index), a path, an empty value, a plain word or
    number (`typesafe`, `4096`), a UUID. A secret has 8 to 200 characters, no spaces, at least one letter and one digit
    or symbol. This trades away short, plain-word and all-digit passwords: the assignment rule catches obvious literals,
    the token-prefix rules catch known formats, and everything else is Jev's call (it sees the redacted text).
    """
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    if not 8 <= len(v) <= 200 or re.search(r"\s", v):
        return False
    if v[0] in "$`(~/." or re.search(r"[(){}\[\]<>]", v) or UUID_VALUE.match(v):
        return False
    has_letter = re.search(r"[A-Za-z]", v) is not None
    return has_letter and re.search(r"[0-9!@#%^&*]", v) is not None


def literal_secret(text: str) -> List[str]:
    kinds = []
    for name, rx in (("private key block", PEM), ("known token prefix", TOKEN_PREFIXES), ("jwt", JWT),
                     ("auth header", AUTH_LITERAL), ("bearer token", BEARER_LITERAL), ("url credentials", URL_CREDS)):
        if rx.search(text):
            kinds.append(name)
    if any(looks_like_secret_value(m.group(3)) for m in ASSIGN.finditer(text)):
        kinds.append("secret-named assignment")
    if SECRET_FLAG.search(text):
        kinds.append("secret flag with literal value")
    return sorted(set(kinds))


# ---- 2. commands that print secrets --------------------------------------------------------------
READERS = r"(?:cat|head|tail|less|more|cp|scp|strings|xxd|base64|bat|source)"
SECRET_PRINTING = [
    ("keychain read", re.compile(r"\bsecurity\s+(?:find-(?:generic|internet)-password\b[^\n;|&]*\s-w\b|dump-keychain)")),
    ("private key read", re.compile(rf"\b{READERS}\b[^\n;|&]*(?:~|\$HOME|/Users/[^/\s]+)/\.ssh/(?!config\b|known_hosts\b|authorized_keys\b)(?!\S*\.pub\b)\S+")),
    ("pem read", re.compile(rf"\b{READERS}\b[^\n;|&]*\.pem\b")),
    ("gpg secret export", re.compile(r"\bgpg\b[^\n;|&]*--export-secret-(?:keys|subkeys)\b")),
    ("environment dump", re.compile(r"(?:^|[;&]\s*|\n)\s*(?:printenv|env)\s*(?:$|[;&\n])")),
    (".env contents", re.compile(rf"(?:\b{READERS}\b|(?<![\w])\.\s)[^\n;|&]*(?<![\w.])\.env(?![\w])(?!\.(?:example|sample|template))|curl\b[^\n]*-d\s*@\S*\.env\b")),
]


def secret_printing(text: str) -> List[str]:
    return sorted({name for name, rx in SECRET_PRINTING if rx.search(text)})


# ---- 3. destructive and irreversible seeds ------------------------------------------------------
BROAD = {"/", "~", "~/", "$HOME", "$HOME/", "${HOME}", "/Users", "/*", "~/*", "$HOME/*", "*", ".", "./", "..", "../", "./*"}
RM = re.compile(r"\brm\s+((?:-[A-Za-z]+\s+|--[a-z\-]+\s+)+)([^;&|\n]+)")
FORCE_PUSH = re.compile(r"\bgit\s+push\b[^\n;|&]*(?:--force\b|--force-with-lease\b|\s-f\b|\s\+\S)")
PIPE_SHELL = re.compile(r"\|\s*(?:sudo\s+)?(?:ba|z|da|fi)?sh\b(?![\w-])|\b(?:ba|z)?sh\s+<\(|\bsource\s+<\(|\beval\s+\"?\$\(\s*(?:curl|wget)")


def destructive_seed(text: str) -> List[str]:
    kinds = []
    if re.search(r"\bsudo\b", text):
        kinds.append("sudo")
    for m in RM.finditer(text):
        if not re.search(r"-[A-Za-z]*[rRf]|--recursive|--force", m.group(1)):
            continue
        for tok in m.group(2).split():
            bare = tok.strip("'\"")
            t = bare if bare in ("/", "~/", "$HOME/") else bare.rstrip("/")
            if t in BROAD or re.fullmatch(r"/Users/[^/]+", t):
                kinds.append("rm on home, root or whole directory")
    if FORCE_PUSH.search(text):
        kinds.append("force push")
    if PIPE_SHELL.search(text):
        kinds.append("pipe to shell")
    return sorted(set(kinds))


# ---- 4. agent-configuration commands (a deliberate exception to "only from logged misses") -------
AGENT_CLI = re.compile(r"\bclaude\s+(?:plugin\s+(?:install|marketplace\s+add|add)|mcp\s+add)\b")


def agent_cli(text: str) -> List[str]:
    return ["adds a plugin, marketplace or MCP server"] if AGENT_CLI.search(text) else []


# ---- 4b. the gate's own maintenance commands: an agent must not init, prune or rewire the gate through its scripts ----
GATE_MAINTENANCE = re.compile(r"\bdoctor\.py\b[^\n;|&]*--(?:init|prune)\b")


def gate_maintenance(text: str) -> List[str]:
    return ["runs the gate's init or prune"] if GATE_MAINTENANCE.search(text) else []


# ---- 5. protected paths: a WRITE whose target is protected (a mention or a read never escalates) ----
PROTECTED = [
    ("agent configuration", re.compile(r"(?:^|[/\s\"'=~$])\.claude(?:\.json)?(?:/|$|[\s\"'])")),
    ("MCP configuration", re.compile(r"(?:^|/)\.mcp\.json\b")),
    ("shell profile", re.compile(r"(?:^|/)\.(?:zshrc|zprofile|zshenv|bashrc|bash_profile|profile)(?![\w.])")),
    ("scheduled jobs", re.compile(r"LaunchAgents/|LaunchDaemons/|/var/spool/cron|/etc/cron")),
    ("system configuration", re.compile(r"(?<![\w.~])/etc/")),
    ("ssh configuration", re.compile(r"\.ssh/(?:config|authorized_keys)\b")),
    # `jev-gate` is deliberately not `permission-gate`, so editing the planning tickets does not trip this.
    ("the gate's own files", re.compile(r"jev[-_]gate|typesafe_permission_gate")),
]
SCHED_COMMAND = re.compile(r"\bcrontab\s+(?:-e\b|-\s*$|-\s*[;&|]|[^\s-]\S*)|\blaunchctl\s+(?:load|bootstrap|enable|submit)\b|(?:\|\s*)crontab\s+-")
WRITERS = {"tee", "mv", "cp", "rm", "rmdir", "ln", "install", "chmod", "chown", "chgrp", "truncate", "touch", "unlink"}
REDIRECT = re.compile(r"(?<![<>&\d])\d?>>?\|?\s*([^\s;|&<>]+)")
PY_WRITE = re.compile(r"open\([^)]*,\s*['\"][wa][b+]?['\"]|\.write_text\(|\.write_bytes\(|shutil\.(?:copy|move)")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")
INTERPRETER = re.compile(r"\b(?:python3?|node|bash|sh|zsh|perl|ruby)\b")


def strip_data_heredocs(text: str) -> str:
    """Drop the body of a heredoc that only feeds data (cat >> f <<EOF); keep one that feeds a shell or interpreter."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = HEREDOC.search(line)
        if m and "<<<" not in line:
            marker = m.group(1)
            j = i + 1
            while j < len(lines) and lines[j].strip() != marker:
                j += 1
            if INTERPRETER.search(line):
                out.extend(lines[i + 1: j])
            i = j  # a data heredoc's body is skipped; an interpreter heredoc's body was kept above
        i += 1
    return "\n".join(out)


def _statements(text: str) -> List[str]:
    return [s for s in re.split(r";|&&|\|\||\||\n", text) if s.strip()]


def _tokens(stmt: str) -> List[str]:
    return [t.strip("'\"") for t in re.findall(r"\"[^\"]*\"|'[^']*'|\S+", stmt)]


def write_targets(stmt: str) -> List[str]:
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


def protected_write(text: str) -> List[str]:
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


def protected_file_path(file_path: str) -> List[str]:
    """Write, Edit, NotebookEdit: the path is the target (Claude Code gives it absolute and ~-expanded)."""
    return sorted({name for name, rx in PROTECTED if rx.search(file_path)})


# ---- the stage -------------------------------------------------------------------------------------
Hit = Tuple[str, List[str]]


def precheck(tool: str, text: str) -> Optional[Hit]:
    """(rule family, pattern types) when the pre-check escalates, else None. `text` is the command for
    Bash and the file path for Write, Edit and NotebookEdit."""
    if tool == "Bash":
        # Data heredocs are text, not commands: only the literal-secret rule reads them.
        body = strip_data_heredocs(text)
        for family, fn, src in (("literal secret", literal_secret, text), ("prints secrets", secret_printing, body),
                                ("destructive seed", destructive_seed, body), ("protected write", protected_write, text),
                                ("agent configuration command", agent_cli, body), ("gate maintenance command", gate_maintenance, body)):
            kinds = fn(src)
            if kinds:
                return family, kinds
    elif tool in ("Write", "Edit", "NotebookEdit"):
        kinds = protected_file_path(text)
        if kinds:
            return "protected write", kinds
    return None


def reason(family: str, kinds: List[str]) -> str:
    """The text shown in the `ask` prompt: rule names only, never matched text."""
    return f"Jev gate: {family} ({', '.join(kinds)})"


# ---- fast path: provably local, read-only commands. Returns no opinion, never allow. ----------------
_SHELL_META = re.compile(r"[;|&<>$`()\n\\]")
_FAST_PATH_PREFIXES = ("ls", "pwd", "whoami", "date", "wc", "which",
                       "git status", "git diff", "git log", "git show", "git branch")


def fast_path(command: str) -> bool:
    command = command.strip()
    if not command or _SHELL_META.search(command):
        return False
    return any(command == p or command.startswith(p + " ") for p in _FAST_PATH_PREFIXES)
