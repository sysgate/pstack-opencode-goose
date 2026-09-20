#!/usr/bin/env python3
"""doctor: check the gate is healthy and maintain it (slices 1, 4, 5 and 6 of docs/permission-gate/SPEC.md).

    python3 doctor.py                      # health checks, exit 0 unless something FAILs
    python3 doctor.py --live               # also one real Jev call on an invented command
    python3 doctor.py --init               # create ~/.config/jev-gate and ~/.local/state/jev-gate, in TRIAL mode
    python3 doctor.py --verify             # check the audit log hash chains
    python3 doctor.py --reconcile [--since DAY] [--transcripts DIR]
                                           # compare the log with session transcripts; a gap means the gate was not running.
                                           # Transcripts are read from $JEV_GATE_HOME/.claude/projects (normally ~/.claude/projects);
                                           # with an isolated JEV_GATE_HOME, point --transcripts at the real folder.
    python3 doctor.py --prune [--yes]      # list (or with --yes delete) monthly logs older than 90 days
    python3 doctor.py --print-entry        # print the hook settings entry for review; writes nothing
    python3 doctor.py --settings FILE ...  # also verify the entry in these settings files

Never prints a secret: it only asks whether the API key can be found.
The mode (trial or enforce) is changed by editing config.json yourself; doctor has no switch for it on purpose.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit  # noqa: E402
import config  # noqa: E402
import heartbeat  # noqa: E402
import precheck  # noqa: E402

GATE = os.path.join(HERE, "gate.py")
PINNED_PYTHON = "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
MATCHER = r"^(Bash|Write|Edit|NotebookEdit)$|^mcp__"
HOOK_TIMEOUT_SECONDS = 5  # above the gate's own 3 second deadline, so its ask arrives before Claude Code cancels it
FALLBACK_JSON = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                   "permissionDecisionReason": "Jev gate failed to run; confirm manually."}},
                           separators=(",", ":"))


def hook_command(python: str = PINNED_PYTHON, gate: str = GATE) -> str:
    """Shell form, so `||` can turn a missing script or interpreter, an import error or a crash into an ask."""
    return f"{shlex.quote(python)} {shlex.quote(gate)} || printf '%s' '{FALLBACK_JSON}'"


SESSION_START_TIMEOUT_SECONDS = 5  # Claude's first response waits for SessionStart hooks; the check takes well under a second


def session_start_command(python: str = PINNED_PYTHON, gate: str = GATE) -> str:
    """The self-check: inline shell that does not depend on the gate script (see heartbeat.py)."""
    return heartbeat.command(python, gate)


def settings_entry() -> dict:
    return {"hooks": {
        "PreToolUse": [{"matcher": MATCHER, "hooks": [
            {"type": "command", "command": hook_command(), "timeout": HOOK_TIMEOUT_SECONDS}]}],
        # no matcher: the self-check runs for every session source (startup, resume, clear, compact)
        "SessionStart": [{"hooks": [
            {"type": "command", "command": session_start_command(), "timeout": SESSION_START_TIMEOUT_SECONDS}]}]}}


class Report:
    def __init__(self):
        self.failed = False

    def line(self, level: str, message: str):
        if level == "FAIL":
            self.failed = True
        print(f"{level:<5} {message}")


def run_hook(command: str, event: dict, env=None) -> str:
    done = subprocess.run(["sh", "-c", command], input=json.dumps(event), capture_output=True, text=True, timeout=15, env=env)
    return done.stdout


def check_interpreter(r: Report):
    if not (os.path.isfile(PINNED_PYTHON) and os.access(PINNED_PYTHON, os.X_OK)):
        return r.line("FAIL", f"pinned interpreter missing or not executable: {PINNED_PYTHON}")
    out = subprocess.run([PINNED_PYTHON, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], capture_output=True, text=True)
    version = tuple(int(x) for x in out.stdout.strip().split(".")) if out.returncode == 0 else (0, 0)
    r.line("OK" if version >= (3, 9) else "FAIL", f"interpreter runs, Python {out.stdout.strip() or 'unknown'} (needs 3.9 or later)")


def check_script(r: Report):
    if not os.path.isfile(GATE):
        return r.line("FAIL", f"gate script missing: {GATE}")
    r.line("OK", "gate script present")


def check_config(r: Report):
    """Returns the loaded config, or None. A missing or bad config means the gate asks about everything."""
    if os.environ.get("JEV_GATE_HOME"):
        r.line("WARN", "JEV_GATE_HOME is set in this environment: the gate would look for its config elsewhere")
    try:
        cfg = config.load()
    except config.ConfigError as exc:
        r.line("FAIL", f"config problem ({exc}): the gate asks about every call until fixed; run --init to create one")
        return None
    r.line("OK", f"config valid: mode {cfg.mode}, threshold {cfg.threshold}, wording {cfg.wording}, {len(cfg.skip_list)} skipped MCP tools")
    if cfg.mode == "trial":
        r.line("INFO", "trial mode: the gate records what it would do and never asks")
    for label, path in (("config directory", cfg.config_dir), ("state directory", cfg.state_dir)):
        protected = bool(precheck.protected_file_path(path + "/x"))
        r.line("OK" if protected else "FAIL", f"{label} is a protected path" if protected else f"{label} is NOT a protected path: the agent could rewrite it")
    return cfg


def check_audit(r: Report, cfg):
    files = audit.files(cfg.state_dir) if cfg else []
    if not files:
        return r.line("INFO", "no audit log yet")
    bad = [(f, audit.verify(f)) for f in files]
    for path, (ok, count, line) in bad:
        name = os.path.basename(path)
        r.line("OK" if ok else "FAIL", f"{name}: chain intact, {count} records" if ok else f"{name}: chain BROKEN at line {line}")


def check_self_test(r: Report):
    """Run the real hook command with one benign and one risky event, against a throwaway enforce-mode config."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "JEV_GATE_HOME": tmp, "TYPESAFE_API_KEY": "", "JEV_GATE_NO_KEYCHAIN": "1"}
        old = os.environ.get("JEV_GATE_HOME")
        os.environ["JEV_GATE_HOME"] = tmp
        try:
            config.init("enforce")
        finally:
            os.environ.pop("JEV_GATE_HOME") if old is None else os.environ.__setitem__("JEV_GATE_HOME", old)
        command = hook_command()
        quiet = run_hook(command, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}, env)  # fast path
        loud = run_hook(command, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "sudo ls"}}, env)
    try:
        decision = json.loads(loud)["hookSpecificOutput"]["permissionDecision"] if loud else None
    except (ValueError, KeyError):
        decision = None
    r.line("OK" if quiet == "" else "FAIL", "a fast-path command gets no opinion" if quiet == "" else "a fast-path command produced output")
    r.line("OK" if decision == "ask" else "FAIL", "a risky command is escalated with ask" if decision == "ask" else "a risky command was not escalated")


def check_key(r: Report):
    """Only asks whether a key exists; never prints it. Without one the gate asks about every judged command."""
    if os.environ.get("TYPESAFE_API_KEY"):
        return r.line("OK", "API key found in the environment")
    found = subprocess.run(["security", "find-generic-password", "-s", "typesafe"], capture_output=True).returncode == 0
    r.line("OK" if found else "FAIL", "API key found in the Keychain" if found
           else "no API key in the environment or Keychain: the gate would ask about every judged command")


def check_live(r: Report):
    """One real Jev call on an invented command, made by the pinned interpreter (the one the hook uses, not the one
    running doctor): proves the key, the certificates, the network, the request shape and the answer parsing."""
    import time
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import jev; "
            "print(json.dumps(jev.judge('Bash', 'rm -rf ~/Documents/*')))")
    started = time.time()
    try:
        done = subprocess.run([PINNED_PYTHON, "-c", code, HERE], capture_output=True, text=True, timeout=15)
        probs = json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError) as exc:  # report the type only
        return r.line("FAIL", f"live call failed ({type(exc).__name__})")
    if not probs:
        kind = (done.stderr.strip().splitlines() or ["?"])[-1].split(":")[0][:60]   # the exception type, never a message
        return r.line("FAIL", f"live call failed under {PINNED_PYTHON} ({kind})")
    top = max(probs, key=probs.get)
    r.line("OK", f"live call answered in {round((time.time() - started) * 1000)} ms; an invented risky command scored highest on {top} ({probs[top]:.2f})")


def cache_claude_version(r: Report, cfg):
    """The hook event does not carry the Claude Code version, so doctor caches it for the audit log."""
    if not cfg:
        return
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10).stdout.split()
        version = out[0] if out and re.fullmatch(r"[0-9][0-9A-Za-z.\-]*", out[0]) else ""
    except (OSError, subprocess.SubprocessError):
        version = ""
    if not version:
        return r.line("WARN", "could not read the Claude Code version; the audit log will record it as unknown")
    path = os.path.join(cfg.state_dir, "claude_version.txt")
    with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as fh:
        fh.write(version + "\n")
    r.line("OK", f"Claude Code {version} (cached for the audit log)")


def check_settings(r: Report, paths):
    if not paths:
        return r.line("INFO", "no settings file given; pass --settings FILE to verify an installed entry")
    want = settings_entry()["hooks"]
    for path in paths:
        if not os.path.isfile(path):
            r.line("INFO", f"{path}: not present, so the gate is not installed there (expected until slice 7)")
            continue
        try:
            cfg = json.load(open(path))
        except ValueError:
            r.line("FAIL", f"{path}: not valid JSON")
            continue
        hooks = cfg.get("hooks") or {}
        for event, label in (("PreToolUse", "gate hook"), ("SessionStart", "self-check hook")):
            ours = [e for e in hooks.get(event, []) for h in e.get("hooks", [])
                    if "jev-gate" in str(h.get("command", "")) or "gate.py" in str(h.get("command", ""))]
            if not ours:
                r.line("INFO" if event == "PreToolUse" else "WARN", f"{path}: no {label} entry" + (", so the gate is not installed there" if event == "PreToolUse"
                       else ": without it there is no heartbeat and no warning when the gate stops working"))
                continue
            ok = ours == want[event]
            r.line("OK" if ok else "FAIL", f"{path}: {label} " + ("matches the spec" if ok else "differs from the spec (matcher, timeout or command); run --print-entry to compare"))


def check_heartbeat(r: Report, cfg):
    if not cfg:
        return
    import datetime
    beats = heartbeat.records(cfg.state_dir)
    if not beats:
        return r.line("INFO", "no heartbeat yet (written by the SessionStart self-check once it is installed)")
    last = beats[-1]
    age = datetime.datetime.now(datetime.timezone.utc) - audit.parse_ts(last["ts"])
    ok = bool(last.get("ok"))
    r.line("OK" if ok else "WARN", f"last heartbeat {last['ts']} ({int(age.total_seconds() // 3600)} h ago): " +
           ("self-check passed" if ok else f"self-check FAILED ({last.get('problems')})"))
    bad = sum(1 for b in beats if not b.get("ok"))
    if bad:
        r.line("WARN", f"{bad} of {len(beats)} heartbeats reported a failed self-check")


def do_init() -> int:
    try:
        path = config.init("trial")
    except FileExistsError:
        print("config already exists; doctor never overwrites it. Edit it yourself if you need a change.")
        return 1
    print(f"created {path} in TRIAL mode (records what the gate would do; never asks)")
    print(f"state directory: {config.state_dir()}")
    return 0


def do_verify() -> int:
    try:
        cfg = config.load()
    except config.ConfigError as exc:
        print(f"FAIL  config problem ({exc})")
        return 1
    r = Report()
    check_audit(r, cfg)
    return 1 if r.failed else 0


def do_reconcile(since, transcripts=None) -> int:
    import datetime
    import reconcile
    try:
        cfg = config.load()
    except config.ConfigError as exc:
        print(f"FAIL  config problem ({exc})")
        return 1
    day = datetime.datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc) if since else None
    root = os.path.abspath(os.path.expanduser(transcripts)) if transcripts else None
    if root and not os.path.isdir(root):
        print(f"FAIL  transcripts folder not found: {root}")
        return 1
    result = reconcile.reconcile(cfg, day, root)
    for line in reconcile.format_report(result):
        print(line)
    return 1 if reconcile.summary(result)["fail"] else 0


def do_prune(yes: bool) -> int:
    try:
        cfg = config.load()
    except config.ConfigError as exc:
        print(f"FAIL  config problem ({exc})")
        return 1
    old = audit.prune(cfg.state_dir, days=90, dry_run=not yes)
    for path in old:
        print(("deleted " if yes else "would delete ") + os.path.basename(path))
    print(f"{len(old)} monthly log(s) older than 90 days" + ("" if yes else "; nothing deleted (add --yes)"))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print-entry", action="store_true", help="print the settings entry and exit; writes nothing")
    ap.add_argument("--settings", action="append", default=[], help="a settings file whose entry should be verified")
    ap.add_argument("--live", action="store_true", help="also make one real Jev call on an invented command")
    ap.add_argument("--init", action="store_true", help="create the config and state directories in trial mode")
    ap.add_argument("--verify", action="store_true", help="check the audit log hash chains")
    ap.add_argument("--prune", action="store_true", help="list monthly logs older than 90 days")
    ap.add_argument("--yes", action="store_true", help="with --prune: actually delete")
    ap.add_argument("--reconcile", action="store_true", help="compare the audit log with session transcripts")
    ap.add_argument("--since", help="with --reconcile: first day, YYYY-MM-DD (default: the first audit record)")
    ap.add_argument("--transcripts", metavar="DIR", help="with --reconcile: read session transcripts from DIR (default: $JEV_GATE_HOME/.claude/projects)")
    a = ap.parse_args(argv)
    if a.transcripts and not a.reconcile:
        ap.error("--transcripts only makes sense with --reconcile")
    if a.reconcile:
        return do_reconcile(a.since, a.transcripts)
    if a.init:
        return do_init()
    if a.verify:
        return do_verify()
    if a.prune:
        return do_prune(a.yes)
    if a.print_entry:
        print(json.dumps(settings_entry(), indent=2))
        return 0
    r = Report()
    check_interpreter(r)
    check_script(r)
    if not r.failed:
        check_self_test(r)
    cfg = check_config(r)
    check_audit(r, cfg)
    check_heartbeat(r, cfg)
    cache_claude_version(r, cfg)
    check_key(r)
    if a.live and not r.failed:
        check_live(r)
    check_settings(r, a.settings)
    return 1 if r.failed else 0


if __name__ == "__main__":
    sys.exit(main())
