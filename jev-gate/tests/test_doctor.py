import json
import os

import pytest

import doctor
import gate


def test_the_settings_entry_follows_the_spec():
    entry = doctor.settings_entry()["hooks"]["PreToolUse"][0]
    assert entry["matcher"] == r"^(Bash|Write|Edit|NotebookEdit)$|^mcp__"
    hook = entry["hooks"][0]
    assert hook["type"] == "command" and hook["timeout"] == 5
    assert hook["timeout"] > gate.DEADLINE_SECONDS            # the gate's own ask must arrive before Claude Code cancels it
    assert " || printf " in hook["command"]                   # the shell fallback
    assert hook["command"].startswith(doctor.PINNED_PYTHON) or hook["command"].startswith("'" + doctor.PINNED_PYTHON)


def test_the_matcher_is_anchored():
    import re
    rx = re.compile(doctor.MATCHER)
    for name in ("Bash", "Write", "Edit", "NotebookEdit", "mcp__schwab__schwab_place_order"):
        assert rx.search(name)
    for name in ("MyBashTool", "WebEditor", "Read", "Task", "EditNotebook"):
        assert not rx.search(name)


def test_print_entry_writes_nothing_and_prints_json(capsys):
    assert doctor.main(["--print-entry"]) == 0
    assert json.loads(capsys.readouterr().out)["hooks"]["PreToolUse"]


def test_reconcile_with_no_log_yet_is_informational(capsys):
    assert doctor.main(["--reconcile"]) == 0
    assert "nothing to reconcile" in capsys.readouterr().out


def test_settings_verification(tmp_path, capsys):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(doctor.settings_entry()))
    r = doctor.Report()
    doctor.check_settings(r, [str(good)])
    assert not r.failed and "matches the spec" in capsys.readouterr().out

    bad = doctor.settings_entry()
    bad["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] = 60
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    r = doctor.Report()
    doctor.check_settings(r, [str(tmp_path / "bad.json")])
    assert r.failed

    r = doctor.Report()
    doctor.check_settings(r, [str(tmp_path / "absent.json")])
    assert not r.failed and "not installed" in capsys.readouterr().out


def _has_key():
    import subprocess
    return bool(os.environ.get("TYPESAFE_API_KEY")) or subprocess.run(["security", "find-generic-password", "-s", "typesafe"], capture_output=True).returncode == 0


@pytest.mark.skipif(not os.path.exists(doctor.PINNED_PYTHON) or not _has_key(), reason="pinned interpreter or API key not available")
def test_the_health_check_passes_here(capsys):
    assert doctor.main([]) == 0
    out = capsys.readouterr().out
    assert "FAIL" not in out and "a risky command is escalated with ask" in out and "a fast-path command gets no opinion" in out
