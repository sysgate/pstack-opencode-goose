"""Reconcile: the audit log against session transcripts. Transcripts here are synthetic and tiny."""
import datetime
import json
import os
import subprocess
import sys

import pytest

import audit
import config
import reconcile
from conftest import make_home

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 9, 14, 9, 0, tzinfo=UTC)
CHI = "/Users/x/Projects/chi"


def at(minutes):
    return T0 + datetime.timedelta(minutes=minutes)


def iso(when):
    return when.strftime("%Y-%m-%dT%H:%M:%S.000Z")


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = make_home(tmp_path / "home", "trial", scopes={"chi": CHI})
    monkeypatch.setenv("JEV_GATE_HOME", home)
    return config.load()


def log(cfg, session, tool, minute):
    audit.append(cfg.state_dir, {"ts": iso(at(minute)), "session": session, "tool": tool, "verdict": "no_opinion", "decider": "fast_path"}, at(minute))


def transcript(name, session, calls, cwd=CHI, sub=""):
    """calls: [(tool name, minute)]"""
    folder = os.path.join(reconcile.projects_root(), "-proj", sub)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name + ".jsonl"), "a") as fh:
        for tool, minute in calls:
            fh.write(json.dumps({"sessionId": session, "cwd": cwd, "timestamp": iso(at(minute)),
                                 "message": {"content": [{"type": "tool_use", "name": tool, "input": {"command": "x"}}]}}) + "\n")


def row(result, session):
    return next(r for r in result["rows"] if r["session"] == session)


def test_matching_counts_are_ok(env):
    for i, tool in enumerate(("Bash", "Bash", "Write")):
        log(env, "s1", tool, i)
    transcript("s1", "s1", [("Bash", 0), ("Bash", 1), ("Write", 2)])
    result = reconcile.reconcile(env)
    r = row(result, "s1")
    assert (r["status"], r["expected"], r["logged"], r["gap"]) == ("OK", 3, 3, 0)
    assert r["per_tool"] == {"Bash": (2, 2), "Write": (1, 1)}
    assert reconcile.summary(result) == {"sessions": 1, "expected": 3, "logged": 3, "fail": 0, "warn": 0}


def test_one_missing_call_warns_and_more_than_one_fails(env):
    log(env, "warn", "Bash", 0)
    transcript("warn", "warn", [("Bash", 0), ("Bash", 1)])
    for i in range(2):
        log(env, "fail", "Bash", i)
    transcript("fail", "fail", [("Bash", 0), ("Bash", 1), ("Bash", 2), ("Bash", 3), ("Bash", 4)])
    result = reconcile.reconcile(env)
    assert row(result, "warn")["status"] == "WARN" and row(result, "fail")["status"] == "FAIL" and row(result, "fail")["gap"] == 3
    assert reconcile.summary(result)["fail"] == 1
    assert any(l.startswith("FAIL") for l in reconcile.format_report(result))


def test_a_session_with_transcript_calls_but_no_records_fails(env):
    log(env, "logged", "Bash", 0)                         # the gate was running in another session
    transcript("logged", "logged", [("Bash", 0)])
    transcript("silent", "silent", [("Bash", 5), ("mcp__x__y", 6)])
    r = row(reconcile.reconcile(env), "silent")
    assert r["status"] == "FAIL" and "was the gate running" in r["why"]


def test_calls_before_the_first_record_and_unmatched_tools_are_ignored(env):
    log(env, "s", "Bash", 10)
    log(env, "s", "Bash", 11)
    transcript("s", "s", [("Bash", 1), ("Bash", 2), ("Bash", 10), ("Bash", 11), ("Read", 12), ("Grep", 13), ("Task", 14)])
    assert row(reconcile.reconcile(env), "s")["status"] == "OK"        # two calls predate the first audit record; Read, Grep, Task are not matched


def test_sessions_outside_the_configured_scopes_are_ignored(env):
    log(env, "in", "Bash", 0)
    transcript("in", "in", [("Bash", 0)])
    transcript("out", "out", [("Bash", 1)], cwd="/Users/x/Projects/elsewhere")
    assert [r["session"] for r in reconcile.reconcile(env)["rows"]] == ["in"]


def test_subagent_transcripts_count_toward_their_session(env):
    for i in range(3):
        log(env, "s", "Bash", i)
    transcript("s", "s", [("Bash", 0)])
    transcript("agent-1", "s", [("Bash", 1), ("Bash", 2)], sub="s/subagents")
    assert row(reconcile.reconcile(env), "s")["status"] == "OK"


def test_more_records_than_transcript_calls_is_only_informational(env):
    for i in range(3):
        log(env, "s", "Bash", i)
    transcript("s", "s", [("Bash", 0)])
    r = row(reconcile.reconcile(env), "s")
    assert r["status"] == "INFO" and r["gap"] == -2


def test_records_without_any_transcript_are_informational(env):
    log(env, "gone", "Bash", 0)
    assert row(reconcile.reconcile(env), "gone")["status"] == "INFO"


def test_no_records_no_transcripts_and_bad_lines(env, tmp_path):
    assert reconcile.reconcile(env)["rows"] == [] and "nothing to reconcile" in reconcile.reconcile(env)["note"]
    log(env, "s", "Bash", 0)
    transcript("s", "s", [("Bash", 0)])
    with open(os.path.join(reconcile.projects_root(), "-proj", "s.jsonl"), "a") as fh:
        fh.write("not json\n{}\n[]\n")
    assert row(reconcile.reconcile(env), "s")["status"] == "OK"


def test_without_scopes_every_session_is_compared_and_says_so(tmp_path, monkeypatch):
    home = make_home(tmp_path / "noscope", "trial")
    monkeypatch.setenv("JEV_GATE_HOME", home)
    cfg = config.load()
    log(cfg, "s", "Bash", 0)
    transcript("s", "s", [("Bash", 0)], cwd="/anywhere")
    result = reconcile.reconcile(cfg)
    assert row(result, "s")["status"] == "OK" and "no scopes" in result["note"]


def test_a_real_gate_that_missed_a_call_is_caught(env):
    """Run the real launcher (trial mode, local-only commands, no network) for 2 of 3 transcript calls."""
    for cmd in ("ls", "sudo ls"):
        event = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": "live", "cwd": CHI})
        done = subprocess.run([sys.executable, os.path.join(HERE, "gate.py")], input=event, capture_output=True, text=True, env=dict(os.environ))
        assert done.returncode == 0 and done.stdout == ""
    first = audit.parse_ts(audit.records(env.state_dir)[0]["ts"])
    stamp = lambda s: (first + datetime.timedelta(seconds=s)).isoformat().replace("+00:00", "Z")   # keep the milliseconds
    folder = os.path.join(reconcile.projects_root(), "-proj")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "live.jsonl"), "w") as fh:
        for s in (0, 1, 2):
            fh.write(json.dumps({"sessionId": "live", "cwd": CHI, "timestamp": stamp(s), "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}}) + "\n")
    r = row(reconcile.reconcile(env), "live")
    assert (r["expected"], r["logged"], r["status"]) == (3, 2, "WARN")


# ---- doctor --reconcile --transcripts: an isolated home still reads the real transcript folder -------------------------
def test_transcripts_option_reads_a_folder_outside_the_home(env, tmp_path, capsys):
    import doctor
    log(env, "s1", "Bash", 0)
    real = tmp_path / "real-claude-projects" / "-proj"
    real.mkdir(parents=True)
    (real / "s1.jsonl").write_text(json.dumps({"sessionId": "s1", "cwd": CHI, "timestamp": iso(at(0)),
                                               "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "x"}}]}}) + "\n")
    assert doctor.main(["--reconcile"]) == 0
    assert "no transcript" in capsys.readouterr().out                     # the default looks under the throwaway home
    assert doctor.main(["--reconcile", "--transcripts", str(tmp_path / "real-claude-projects")]) == 0
    out = capsys.readouterr().out
    assert "OK" in out and "every matched call was logged" in out and "no transcript" not in out


def test_transcripts_option_rejects_a_missing_folder_and_a_misuse(env, tmp_path, capsys):
    import doctor
    log(env, "s1", "Bash", 0)
    assert doctor.main(["--reconcile", "--transcripts", str(tmp_path / "nowhere")]) == 1
    assert "transcripts folder not found" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        doctor.main(["--transcripts", str(tmp_path)])

