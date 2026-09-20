#!/usr/bin/env python3
"""Ticket 05 facts: how would candidate local pre-check rules behave on the real command pool?

Counts and shapes only. Never prints command text.
"""

import collections
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..")))
import extract_commands as x  # noqa: E402
import typesafe_permission_gate as gate  # noqa: E402

rows = [json.loads(l) for l in open(os.path.join(x.DATA, "candidates.jsonl"))]
real = [r for r in rows if r["kind"] == "bash" and not r["secret_hit"]]
texts = [r["text"] for r in real]
N = len(real)


def pct(n):
    return f"{n} ({100 * n / N:.1f}%)"


def any_match(rx, flags=0):
    c = re.compile(rx, flags)
    return [bool(c.search(t)) for t in texts]


print(f"usable real Bash commands: {N}\n")

# ---- fast path -------------------------------------------------------------
fp = [gate.fast_path({"tool_name": "Bash", "tool_input": {"command": t}}) for t in texts]
META = re.compile(r"[;|&<>$`()\n\\]")
cd_lead = re.compile(r"^\s*cd\s+(?:\"[^\"]*\"|'[^']*'|\S+)\s*&&\s*(.*)$", re.S)
starts_cd = sum(1 for t in texts if cd_lead.match(t))
cd_then_fast = sum(
    1 for t in texts
    if (m := cd_lead.match(t)) and gate.fast_path({"tool_name": "Bash", "tool_input": {"command": m.group(1)}})
)
print("FAST PATH (current prefix list, no shell metacharacters)")
print("  covered today:", pct(sum(fp)))
print("  contain a shell metacharacter:", pct(sum(bool(META.search(t)) for t in texts)))
print("  start with 'cd <dir> &&':", pct(starts_cd), "| of those, remainder would be fast path:", cd_then_fast)

# ---- candidate always-escalate rules ---------------------------------------
print("\nCANDIDATE ALWAYS-ESCALATE RULES (matches among real commands)")
rules = {}
rules["sudo"] = any_match(r"\bsudo\b")
rules["pipe-to-shell"] = any_match(r"\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b|\bbash\s+<\(|\beval\s+\"?\$\(\s*curl")
rules["git push (any)"] = any_match(r"\bgit\s+push\b")
rules["git push --force"] = any_match(r"\bgit\s+push\b[^;&|]*(?:--force|\s-f\b|--force-with-lease|\s\+[A-Za-z])")

RM = re.compile(r"\brm\s+((?:-[A-Za-z]+\s+|--[a-z\-]+\s+)+)([^;&|\n]+)")


def rm_worst(text):
    order = ["root_or_home", "cwd_wide", "absolute_other", "relative", "regenerable", "temp"]
    found = set()
    for m in RM.finditer(text):
        if not re.search(r"-[A-Za-z]*[rRf]|--recursive|--force", m.group(1)):
            continue
        for tok in m.group(2).split():
            t = tok.strip("'\"")
            if t in ("/", "~", "~/", "$HOME", "$HOME/", "/Users", "/Users/robertlai", "/Users/robertlai/", "/*", "~/*", "$HOME/*"):
                found.add("root_or_home")
            elif t in ("*", ".", "./", "..", "../"):
                found.add("cwd_wide")
            elif t.startswith(("/tmp", "/private/tmp", "/var/folders")):
                found.add("temp")
            elif re.search(r"__pycache__|\.pytest_cache|node_modules|/dist\b|^dist\b|/build\b|^build\b|\.venv|\.scratch", t):
                found.add("regenerable")
            elif t.startswith(("/", "~")):
                found.add("absolute_other")
            else:
                found.add("relative")
    for k in order:
        if k in found:
            return k
    return None


rm_classes = collections.Counter(c for c in (rm_worst(t) for t in texts) if c)
print("  rm with recursive/force flags, by worst target class:", dict(rm_classes) or "none")
rules["rm recursive/force on home, root or cwd-wide"] = [rm_worst(t) in ("root_or_home", "cwd_wide") for t in texts]
rules["rm recursive/force on any non-regenerable target"] = [rm_worst(t) in ("root_or_home", "cwd_wide", "absolute_other", "relative") for t in texts]

SECRETS = {
    "keychain read (security find/dump)": r"\bsecurity\s+(?:find|dump)-(?:generic-password|internet-password|keychain)|\bsecurity\s+dump-keychain",
    "ssh private key or .pem": r"\.ssh/(?!config|known_hosts|authorized_keys)|\bid_(?:rsa|ed25519|ecdsa)\b|\.pem\b",
    ".env file": r"(?<![\w.])\.env(?:\.[a-z]+)?\b",
    "environment dump (env/printenv)": r"(?:^|[;&|]\s*)(?:printenv|env)\s*(?:$|\|)",
    "secret-named variable reference": r"\$\{?[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*\}?",
    "credential files (.netrc, .aws, .npmrc ...)": r"\.netrc|\.aws/credentials|\.npmrc|\.pypirc|\.docker/config\.json",
}
for name, rx in SECRETS.items():
    rules[f"reads secrets: {name}"] = any_match(rx)

PROTECTED = {
    "agent settings/hooks/skills": r"\.claude/(?:settings|hooks|skills|plugins|keybindings)|\.claude\.json",
    "shell profiles": r"\.(?:zshrc|zprofile|zshenv|bashrc|bash_profile|profile)\b",
    "scheduled jobs": r"\bcrontab\b|\blaunchctl\b|LaunchAgents|LaunchDaemons",
    "/etc": r"(?<![\w.])/etc/",
    "MCP config": r"\.mcp\.json",
    "gate files": r"typesafe_permission_gate|permission-gate/(?:data|tools)",
    "ssh config/authorized_keys": r"\.ssh/(?:config|authorized_keys)",
}
WRITEISH = re.compile(r"(?:>>?|\btee\b|\bsed\s+-i|\bmv\b|\bcp\b|\brm\b|\bchmod\b|\bchown\b|\bln\b|\btruncate\b|\btouch\b|<<|write_text|\.write\(|open\([^)]*['\"][wa])")
print("\nPROTECTED PATHS (mentions; mentions together with a write-like verb)")
for name, rx in PROTECTED.items():
    c = re.compile(rx)
    mention = [bool(c.search(t)) for t in texts]
    write = [m and bool(WRITEISH.search(t)) for m, t in zip(mention, texts)]
    print(f"  {name}: mentioned {sum(mention)}, with write-like verb {sum(write)}")
    rules[f"protected write: {name}"] = write

print("\nRULE HIT COUNTS (share of real commands that would escalate locally)")
for name, hits in rules.items():
    print(f"  {name}: {pct(sum(hits))}")

seed = [
    "sudo", "pipe-to-shell", "git push --force", "rm recursive/force on home, root or cwd-wide",
    "reads secrets: keychain read (security find/dump)", "reads secrets: ssh private key or .pem",
    "reads secrets: .env file", "reads secrets: environment dump (env/printenv)",
    "reads secrets: credential files (.netrc, .aws, .npmrc ...)",
] + [k for k in rules if k.startswith("protected write:")]
union = [any(rules[k][i] for k in seed) for i in range(N)]
with_var = [union[i] or rules["reads secrets: secret-named variable reference"][i] for i in range(N)]
print("\nUNION of the proposed v1 seed list (no variable references):", pct(sum(union)))
print("  plus 'secret-named variable reference':", pct(sum(with_var)))
print("  plus 'git push (any)':", pct(sum(with_var[i] or rules["git push (any)"][i] for i in range(N))))

# ---- secret-literal hits: shape only ---------------------------------------
print("\nSECRET-LITERAL HITS in the excluded rows (shape only)")
marker = collections.Counter()
for r in rows:
    if r["secret_hit"]:
        for k in set(re.findall(r"<REDACTED(?::([a-z\-]+))?>", r["text"])):
            marker[k or "assignment/flag/header"] += 1
print("  by rule:", dict(marker))
shapes = []
seen = set()
for folder, path in x.transcript_files():
    for line in open(path, errors="replace"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        for item in (msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), list) else []):
            if not (isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Bash"):
                continue
            body = str((item.get("input") or {}).get("command", ""))
            for m in x.LONG_TOKEN.finditer(body):
                tok = m.group(0)
                if (x.HEX_ONLY.match(tok) and len(tok) <= 64) or x.UUID.match(tok):
                    continue
                if m.start() > 0 and body[m.start() - 1] in "/.":
                    continue
                if not (re.search(r"\d", tok) and re.search(r"[A-Za-z]", tok)) or tok in seen:
                    continue
                seen.add(tok)
                counts = collections.Counter(tok)
                ent = -sum(c / len(tok) * math.log2(c / len(tok)) for c in counts.values())
                shapes.append((len(tok), round(ent, 2), bool(re.search(r"[A-Z]", tok)), bool(re.search(r"[a-z]", tok)),
                               "-" in tok, "_" in tok))
print("  long-token candidates still redacted (len, entropy bits/char, has-upper, has-lower, has-'-', has-'_'):")
for s in sorted(shapes):
    print("   ", s)
