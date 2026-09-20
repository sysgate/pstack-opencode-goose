"""The launcher run as a subprocess on every Python this machine has (3.9 and 3.12 among them)."""
import io
import json
import os
import shutil
import subprocess
import sys
import time

import pytest

import gate
from conftest import ENFORCE_HOME

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [sys.executable, "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3", "/usr/bin/python3"]
INTERPRETERS = sorted({c for c in CANDIDATES if os.path.isfile(c) and os.access(c, os.X_OK)})


# Subprocess runs never reach the network or the Keychain: with no key, a Jev-bound call fails closed to an ask.
SANDBOX_ENV = {**os.environ, "TYPESAFE_API_KEY": "", "JEV_GATE_NO_KEYCHAIN": "1", "JEV_GATE_HOME": ENFORCE_HOME}


def run_gate(interpreter, stdin_text, script=None):
    done = subprocess.run([interpreter, script or os.path.join(HERE, "gate.py")], input=stdin_text, capture_output=True, text=True,
                          timeout=20, env=SANDBOX_ENV)
    return done.returncode, done.stdout


def event(tool, **tool_input):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})


def parse_ask(out):
    body = json.loads(out)["hookSpecificOutput"]
    assert body["hookEventName"] == "PreToolUse" and body["permissionDecision"] == "ask"
    assert isinstance(body["permissionDecisionReason"], str) and body["permissionDecisionReason"]
    return body["permissionDecisionReason"]


@pytest.mark.parametrize("py", INTERPRETERS)
def test_benign_and_unknown_get_no_opinion(py):
    for stdin in (event("Bash", command="ls -la"), event("Write", file_path="/Users/x/Projects/chi/README.md"),
                  event("Edit", file_path="/Users/x/Projects/chi/CLAUDE.md"), event("Read", file_path="/etc/hosts"),
                  json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "sudo ls"}})):
        assert run_gate(py, stdin) == (0, "")


@pytest.mark.parametrize("py", INTERPRETERS)
def test_calls_that_need_jev_fail_closed_without_a_key(py):
    for stdin in (event("Bash", command="echo hello"), event("mcp__schwab__schwab_get_quotes", symbols=["AAPL"])):
        rc, out = run_gate(py, stdin)
        assert rc == 0
        assert "KeyMissing" in parse_ask(out)


@pytest.mark.parametrize("py", INTERPRETERS)
def test_risky_calls_get_an_ask_and_only_an_ask(py):
    cases = [event("Bash", command="sudo ls"), event("Bash", command="claude plugin install x@y"),
             event("Write", file_path="/Users/x/.claude/settings.json"), event("Edit", file_path="/Users/x/.zshrc"),
             event("NotebookEdit", notebook_path="/Users/x/.claude/x.ipynb"), event("NotebookEdit", file_path="/Users/x/.zshrc")]
    for stdin in cases:
        rc, out = run_gate(py, stdin)
        assert rc == 0
        parse_ask(out)
        assert "allow" not in out.replace("permissionDecision", "") and '"deny"' not in out


@pytest.mark.parametrize("py", INTERPRETERS)
def test_bad_input_fails_closed_without_leaking(py):
    for stdin in ("not json", "", "[]", "null", "42"):
        rc, out = run_gate(py, stdin)
        assert rc == 0
        assert "could not decide" in parse_ask(out)


def test_reason_never_contains_the_command_or_the_secret():
    canary = "sk-ant-" + "CANARYCANARY0123" * 3
    out = io.StringIO()
    assert gate.main(io.StringIO(event("Bash", command=f"export API_KEY={canary}")), out) == 0
    assert "CANARY" not in out.getvalue()
    out = io.StringIO()
    gate.main(io.StringIO("{" + canary), out)  # malformed JSON whose text contains the canary
    assert "CANARY" not in out.getvalue()


def test_deadline_turns_a_slow_decision_into_an_ask(monkeypatch):
    monkeypatch.setattr(gate, "DEADLINE_SECONDS", 0.2)
    monkeypatch.setattr(gate, "evaluate", lambda e, c: time.sleep(2))
    out = io.StringIO()
    started = time.time()
    assert gate.main(io.StringIO(event("Bash", command="echo hi")), out) == 0
    assert time.time() - started < 1.5
    assert "DeadlineExceeded" in parse_ask(out.getvalue())


def test_run_with_deadline_restores_the_alarm():
    assert gate.run_with_deadline(lambda: 7, 1.0) == 7
    with pytest.raises(gate.DeadlineExceeded):
        gate.run_with_deadline(lambda: time.sleep(1), 0.1)
    time.sleep(0.2)  # no stray alarm fires afterwards


@pytest.mark.parametrize("py", INTERPRETERS)
def test_import_failure_is_an_ask_not_a_crash(py, tmp_path):
    lone = tmp_path / "gate.py"
    shutil.copy(os.path.join(HERE, "gate.py"), lone)  # precheck.py deliberately absent
    rc, out = run_gate(py, event("Bash", command="echo hi"), script=str(lone))
    assert rc == 0 and "ModuleNotFoundError" in parse_ask(out)


@pytest.mark.parametrize("py", INTERPRETERS)
def test_precheck_imports_on_every_interpreter(py):
    assert subprocess.run([py, "-c", "import precheck"], cwd=HERE, capture_output=True).returncode == 0
