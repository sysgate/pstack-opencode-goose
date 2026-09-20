"""The shell fallback in the exact command shape the spec registers: `PY gate.py || printf '<ask JSON>'`.
Mirrors the headless checks made against the real hook runner (mode-tests/run_wrapper.py)."""
import json
import os
import shutil
import subprocess
import sys

import pytest

import doctor
from conftest import ENFORCE_HOME

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(hook_cmd, tool="Bash", **tool_input):
    stdin = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})
    env = {**os.environ, "TYPESAFE_API_KEY": "", "JEV_GATE_NO_KEYCHAIN": "1", "JEV_GATE_HOME": ENFORCE_HOME}
    done = subprocess.run(["sh", "-c", hook_cmd], input=stdin, capture_output=True, text=True, timeout=20, env=env)
    return done.returncode, done.stdout


def assert_ask(out):
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_a_healthy_gate_stays_quiet_and_still_escalates():
    cmd = doctor.hook_command(PY, os.path.join(HERE, "gate.py"))
    assert run(cmd, command="ls") == (0, "")
    rc, out = run(cmd, command="sudo ls")
    assert rc == 0
    assert_ask(out)
    assert "Jev gate: destructive seed" in out


def test_a_mistyped_script_path_becomes_an_ask():
    rc, out = run(doctor.hook_command(PY, "/nonexistent/gate.py"), command="ls")
    assert rc == 0
    assert_ask(out)


def test_a_mistyped_interpreter_path_becomes_an_ask():
    rc, out = run(doctor.hook_command("/nonexistent/python3", os.path.join(HERE, "gate.py")), command="ls")
    assert rc == 0
    assert_ask(out)


def test_a_crashing_script_becomes_an_ask(tmp_path):
    crash = tmp_path / "crash.py"
    crash.write_text("import sys\nsys.exit(1)\n")
    rc, out = run(doctor.hook_command(PY, str(crash)), command="ls")
    assert rc == 0
    assert_ask(out)


def test_a_script_that_dies_with_a_traceback_becomes_an_ask(tmp_path):
    boom = tmp_path / "boom.py"
    boom.write_text("raise RuntimeError('boom')\n")
    rc, out = run(doctor.hook_command(PY, str(boom)), command="ls")
    assert rc == 0
    assert_ask(out)


def test_paths_with_spaces_are_quoted(tmp_path):
    folder = tmp_path / "a folder with spaces"
    folder.mkdir()
    for name in ("gate.py", "precheck.py", "jev.py", "questions.py", "config.py", "audit.py", "sanitize.py"):
        shutil.copy(os.path.join(HERE, name), folder / name)
    cmd = doctor.hook_command(PY, str(folder / "gate.py"))
    assert run(cmd, command="ls") == (0, "")
    assert_ask(run(cmd, command="sudo ls")[1])


def test_the_fallback_json_is_valid_and_carries_a_reason():
    body = json.loads(doctor.FALLBACK_JSON)["hookSpecificOutput"]
    assert body["hookEventName"] == "PreToolUse" and body["permissionDecision"] == "ask"
    assert "failed to run" in body["permissionDecisionReason"]
    assert "'" not in doctor.FALLBACK_JSON  # it is embedded inside single quotes in the shell command
