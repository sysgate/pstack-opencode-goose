"""The SessionStart self-check (inline shell) and the heartbeat it writes, plus everything that reads heartbeats."""
import datetime
import json
import os
import stat
import subprocess
import sys
import time

import pytest

import audit
import config
import doctor
import heartbeat
import reconcile
import review
from conftest import make_home

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(HERE, "gate.py")
UTC = datetime.timezone.utc


def run_check(tmp_path, *, py=sys.executable, gate=GATE, stdin=None, with_config=True, key="k", extra_env=None, home_name="home"):
    home = tmp_path / home_name
    if with_config:
        make_home(home, "trial")
    else:
        os.makedirs(home, exist_ok=True)
    env = {**os.environ, "JEV_GATE_HOME": str(home), "TYPESAFE_API_KEY": key, "JEV_GATE_NO_KEYCHAIN": "1", **(extra_env or {})}
    event = stdin if stdin is not None else json.dumps({"hook_event_name": "SessionStart", "session_id": "sess-1", "source": "startup"})
    started = time.time()
    done = subprocess.run(["sh", "-c", heartbeat.command(py, gate)], input=event, capture_output=True, text=True, env=env, timeout=20)
    return done, home / ".local" / "state" / "jev-gate", time.time() - started


def beats(state):
    return [json.loads(l) for l in open(os.path.join(state, "heartbeat.jsonl")).read().splitlines()]


# ---- the script ------------------------------------------------------------------------------------------------
def test_a_healthy_session_start_says_nothing_and_writes_a_passing_heartbeat(tmp_path):
    done, state, elapsed = run_check(tmp_path)
    assert (done.returncode, done.stdout) == (0, "")
    (beat,) = beats(state)
    assert (beat["session"], beat["source"], beat["ok"], beat["problems"]) == ("sess-1", "startup", True, "") and beat["ts"].endswith("Z")
    assert elapsed < 1.5


@pytest.mark.parametrize("kwargs, expected", [
    ({"gate": "/nonexistent/gate.py"}, ["script-missing"]),
    ({"py": "/nonexistent/python3"}, ["interpreter-missing"]),
    ({"py": "/usr/bin/false"}, ["interpreter-broken"]),
    ({"with_config": False}, ["config-missing"]),
    ({"key": ""}, ["key-missing"]),
    ({"gate": "/nonexistent/gate.py", "with_config": False, "key": ""}, ["script-missing", "config-missing", "key-missing"]),
])
def test_every_failure_is_named_in_the_heartbeat_and_a_system_message(tmp_path, kwargs, expected):
    done, state, _ = run_check(tmp_path, **kwargs)
    assert done.returncode == 0                                   # a self-check never blocks a session
    beat = beats(state)[-1]
    assert beat["ok"] is False and beat["problems"].split() == expected
    message = json.loads(done.stdout)["systemMessage"]              # valid JSON, and it names each problem
    assert all(p in message for p in expected) and "doctor.py" in message


def test_the_check_works_even_when_the_gate_script_and_interpreter_are_gone(tmp_path):
    done, state, _ = run_check(tmp_path, py="/nonexistent/python3", gate="/nonexistent/gate.py")
    assert done.returncode == 0 and beats(state)[-1]["problems"] == "interpreter-missing script-missing"


def test_hostile_or_missing_input_never_breaks_the_heartbeat(tmp_path):
    hostile = json.dumps({"session_id": 'x"; rm -rf ~ #\\n$(id)`', "source": "a\nb"})
    for i, stdin in enumerate((hostile, "", "not json", "{}")):
        done, state, _ = run_check(tmp_path, stdin=stdin, home_name=f"h{i}")
        assert done.returncode == 0
        (beat,) = beats(state)                                      # exactly one valid JSON line each time
        assert set(beat["session"]) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
        assert set(beat["source"]) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    assert not os.path.exists(os.path.expanduser("~/x"))


def test_the_state_directory_and_file_are_private_and_lines_accumulate(tmp_path):
    home = tmp_path / "fresh"
    os.makedirs(home)
    env = {**os.environ, "JEV_GATE_HOME": str(home), "TYPESAFE_API_KEY": "k", "JEV_GATE_NO_KEYCHAIN": "1"}
    for sid in ("a", "b", "c"):
        subprocess.run(["sh", "-c", heartbeat.command(sys.executable, GATE)], input=json.dumps({"session_id": sid, "source": "resume"}), capture_output=True, text=True, env=env)
    state = home / ".local" / "state" / "jev-gate"
    assert [b["session"] for b in beats(state)] == ["a", "b", "c"]
    assert stat.S_IMODE(os.stat(state / "heartbeat.jsonl").st_mode) == 0o600 and stat.S_IMODE(os.stat(state).st_mode) == 0o700


def test_paths_with_spaces_and_no_secret_extraction(tmp_path):
    folder = tmp_path / "a folder"
    folder.mkdir()
    fake = folder / "gate.py"
    fake.write_text("")
    done, state, _ = run_check(tmp_path, gate=str(fake))
    assert beats(state)[-1]["ok"] is True
    assert " -w" not in heartbeat.SCRIPT and "find-generic-password -s typesafe >/dev/null" in heartbeat.SCRIPT   # existence only, never the value


def test_the_keychain_is_consulted_when_there_is_no_env_key_and_no_opt_out(tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "called"
    (fake_bin / "security").write_text(f"#!/bin/sh\necho \"$@\" > {marker}\nexit 0\n")
    os.chmod(fake_bin / "security", 0o755)
    done, state, _ = run_check(tmp_path, key="", extra_env={"JEV_GATE_NO_KEYCHAIN": "", "PATH": f"{fake_bin}:{os.environ['PATH']}"})
    assert beats(state)[-1]["ok"] is True and "find-generic-password -s typesafe" in marker.read_text()


# ---- the hook entry and doctor ---------------------------------------------------------------------------------------
def test_the_settings_entry_has_both_hooks_and_the_self_check_needs_no_matcher():
    hooks = doctor.settings_entry()["hooks"]
    assert set(hooks) == {"PreToolUse", "SessionStart"}
    start = hooks["SessionStart"][0]
    assert "matcher" not in start and start["hooks"][0]["timeout"] == 5 and start["hooks"][0]["command"] == heartbeat.command(doctor.PINNED_PYTHON, doctor.GATE)
    assert hooks["PreToolUse"][0]["matcher"] == doctor.MATCHER


def test_doctor_verifies_both_installed_entries(tmp_path, capsys):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(doctor.settings_entry()))
    r = doctor.Report()
    doctor.check_settings(r, [str(good)])
    out = capsys.readouterr().out
    assert not r.failed and "gate hook matches the spec" in out and "self-check hook matches the spec" in out

    only_gate = doctor.settings_entry()
    del only_gate["hooks"]["SessionStart"]
    (tmp_path / "gate.json").write_text(json.dumps(only_gate))
    r = doctor.Report()
    doctor.check_settings(r, [str(tmp_path / "gate.json")])
    assert not r.failed and "WARN" in capsys.readouterr().out            # a missing self-check is a warning, not a failure

    changed = doctor.settings_entry()
    changed["hooks"]["SessionStart"][0]["hooks"][0]["timeout"] = 60
    (tmp_path / "changed.json").write_text(json.dumps(changed))
    r = doctor.Report()
    doctor.check_settings(r, [str(tmp_path / "changed.json")])
    assert r.failed


def test_doctor_reports_the_last_heartbeat(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JEV_GATE_HOME", make_home(tmp_path / "h", "trial"))
    cfg = config.load()
    r = doctor.Report()
    doctor.check_heartbeat(r, cfg)
    assert "no heartbeat yet" in capsys.readouterr().out
    os.makedirs(cfg.state_dir, exist_ok=True)
    now = datetime.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    open(heartbeat.path(cfg.state_dir), "w").write(json.dumps({"ts": now, "session": "s", "source": "startup", "ok": True, "problems": ""}) + "\n")
    doctor.check_heartbeat(r, cfg)
    assert "self-check passed" in capsys.readouterr().out
    open(heartbeat.path(cfg.state_dir), "a").write(json.dumps({"ts": now, "session": "t", "source": "startup", "ok": False, "problems": "key-missing"}) + "\n")
    doctor.check_heartbeat(r, cfg)
    out = capsys.readouterr().out
    assert "FAILED (key-missing)" in out and "1 of 2 heartbeats" in out and not r.failed


# ---- reading heartbeats ------------------------------------------------------------------------------------------------
def test_heartbeat_records_filter_by_window_and_skip_bad_lines(tmp_path):
    state = str(tmp_path)
    lines = [{"ts": f"2026-09-{d:02d}T10:00:00Z", "session": f"s{d}", "ok": True} for d in (10, 12, 14)]
    open(heartbeat.path(state), "w").write("\n".join(json.dumps(l) for l in lines) + "\nnot json\n[]\n{\"ts\": \"bad\"}\n")
    assert [b["session"] for b in heartbeat.records(state)] == ["s10", "s12", "s14"]
    since = datetime.datetime(2026, 9, 11, tzinfo=UTC)
    assert [b["session"] for b in heartbeat.records(state, since)] == ["s12", "s14"]
    assert heartbeat.records(str(tmp_path / "none")) == [] and set(heartbeat.by_session(heartbeat.records(state))) == {"s10", "s12", "s14"}


# ---- reconcile: the heartbeat column ------------------------------------------------------------------------------------
T0 = datetime.datetime(2026, 9, 14, 9, 0, tzinfo=UTC)
CHI = "/Users/x/Projects/chi"


def iso(minutes):
    return (T0 + datetime.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def setup_session(cfg, sid, minute, ok_call=True):
    audit.append(cfg.state_dir, {"ts": iso(minute), "session": sid, "tool": "Bash", "verdict": "no_opinion", "decider": "fast_path"}, T0 + datetime.timedelta(minutes=minute))
    folder = os.path.join(reconcile.projects_root(), "-p")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, sid + ".jsonl"), "w") as fh:
        fh.write(json.dumps({"sessionId": sid, "cwd": CHI, "timestamp": iso(minute), "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}}) + "\n")


def beat(cfg, sid, minute, ok=True):
    os.makedirs(cfg.state_dir, exist_ok=True)
    with open(heartbeat.path(cfg.state_dir), "a") as fh:
        fh.write(json.dumps({"ts": iso(minute), "session": sid, "source": "startup", "ok": ok, "problems": "" if ok else "key-missing"}) + "\n")


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_GATE_HOME", make_home(tmp_path / "home", "trial", scopes={"chi": CHI}))
    return config.load()


def hb(result, sid):
    return next(r for r in result["rows"] if r["session"] == sid)


def test_reconcile_heartbeat_states(cfg):
    for i, sid in enumerate(("old", "good", "silent", "broken")):
        setup_session(cfg, sid, i * 10)
    beat(cfg, "good", 15)          # first heartbeat at minute 15: "old" (minute 0) and "good"... started before it? good=10 <15 so also n/a
    assert hb(reconcile.reconcile(cfg), "good")["heartbeat"] == "n/a"
    setup_session(cfg, "late-good", 40); setup_session(cfg, "late-silent", 50); setup_session(cfg, "late-broken", 60)
    beat(cfg, "late-good", 41); beat(cfg, "late-broken", 61, ok=False)
    result = reconcile.reconcile(cfg)
    assert [hb(result, s)["heartbeat"] for s in ("old", "late-good", "late-silent", "late-broken")] == ["n/a", "ok", "missing", "failed"]
    assert hb(result, "late-good")["status"] == "OK"
    assert hb(result, "late-silent")["status"] == "WARN" and "heartbeat is missing" in hb(result, "late-silent")["why"]
    assert hb(result, "late-broken")["status"] == "WARN"
    assert "heartbeat missing" in "\n".join(reconcile.format_report(result))
    assert reconcile.summary(result)["fail"] == 0                     # a heartbeat problem alone never fails the reconcile


def test_reconcile_without_any_heartbeat_says_not_recorded(cfg):
    setup_session(cfg, "s", 0)
    assert hb(reconcile.reconcile(cfg), "s")["heartbeat"] == "not recorded" and hb(reconcile.reconcile(cfg), "s")["status"] == "OK"


# ---- review progress: the heartbeat criterion --------------------------------------------------------------------------------
def rec(sid, minute):
    return {"ts": iso(minute), "session": sid, "tool": "Bash", "decider": "jev", "verdict": "no_opinion", "entry": f"{sid}-{minute}", "signals": None}


def criterion(records, beats_):
    rows = review.progress(records, {}, None, beats_)
    return next((s, d) for n, s, d in rows if n == "Heartbeat present for every session")


def test_progress_heartbeat_criterion():
    records = [rec("a", 0), rec("b", 30), rec("c", 60)]
    assert criterion(records, None)[0] == "NOT YET" and criterion(records, [])[0] == "NOT YET"
    first = {"ts": iso(10), "session": "b", "ok": True}
    status, detail = criterion(records, [first])
    assert status == "NOT YET" and "1 missing" in detail                    # "c" has no heartbeat; "a" began before the first one
    assert criterion(records, [first, {"ts": iso(61), "session": "c", "ok": True}])[0] == "MET"
    status, detail = criterion(records, [first, {"ts": iso(61), "session": "c", "ok": False}])
    assert status == "NOT YET" and "1 failed" in detail
    assert criterion(records, [first, {"ts": iso(61), "session": "c", "ok": False}, {"ts": iso(62), "session": "c", "ok": True}])[0] == "MET"
