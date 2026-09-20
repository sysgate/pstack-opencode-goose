"""The weekly review: selection, statistics, marks, exit-criteria progress and the page."""
import datetime
import json
import os
import re
import shutil
import stat
import subprocess

import pytest

import audit
import config
import review
from conftest import make_home

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 9, 14, 9, 0, tzinfo=UTC)
SIGNALS = ("destructive", "external_effect", "reads_secrets", "uploads_data", "runs_downloaded", "tampers_config")


def sig(top=0.05, name="destructive"):
    return {s: (top if s == name else 0.02) for s in SIGNALS}


def add(cfg, i, _step=1.0, **kw):
    """Append a record i steps after T0 (a step is _step hours)."""
    when = T0 + datetime.timedelta(hours=i * _step)
    record = {"ts": when.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "session": "s", "tool": "Bash", "prefix": f"cmd {i}", "secret_types": None,
              "signals": sig(), "verdict": "no_opinion", "decider": "jev", "rule_family": None, "latency_ms": 250, "mode": "trial",
              "threshold": 0.4, "wording": "v2", "hook": "0.4.0", "claude_code": "2.1.278"}
    record.update(kw)
    audit.append(cfg.state_dir, record, when)


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_GATE_HOME", make_home(tmp_path / "home", "trial"))
    return config.load()


def load(cfg):
    return audit.records(cfg.state_dir)


# ---- selection ------------------------------------------------------------------------------------------------
def test_flagged_near_threshold_and_a_seeded_sample_of_the_rest(cfg):
    for i in range(3):
        add(cfg, i, verdict="would_ask", signals=sig(0.8))
    for i in range(3, 6):
        add(cfg, i, signals=sig(0.3))                                     # near: 0.25 up to 0.4
    add(cfg, 6, signals=sig(0.39)); add(cfg, 7, signals=sig(0.24))       # 0.39 is near, 0.24 is not
    for i in range(8, 108):
        add(cfg, i)                                                       # 100 ordinary calls plus the 0.24 one
    flagged, near, sample, rest = review.select(load(cfg), "seed-a")
    assert len(flagged) == 3 and len(near) == 4 and rest == 101 and len(sample) == 10
    assert not {r["entry"] for r in sample} & {r["entry"] for r in near + flagged}
    assert [r["entry"] for r in sample] == [r["entry"] for r in review.select(load(cfg), "seed-a")[2]]      # reproducible
    assert {r["entry"] for r in sample} != {r["entry"] for r in review.select(load(cfg), "seed-b")[2]}       # another seed, another sample


def test_a_records_own_threshold_defines_near_and_small_pools_still_get_one(cfg):
    add(cfg, 0, signals=sig(0.55), threshold=0.6)                         # near, because this record's threshold was 0.6
    add(cfg, 1)
    flagged, near, sample, rest = review.select(load(cfg), "s")
    assert (len(flagged), len(near), len(sample), rest) == (0, 1, 1, 1)
    assert review.select([], "s") == ([], [], [], 0)


# ---- statistics ----------------------------------------------------------------------------------------------------
def test_statistics(cfg):
    for i, (verdict, lat, decider) in enumerate([("would_ask", 100, "jev"), ("would_ask", 300, "jev"), ("no_opinion", 200, "fast_path"), ("would_ask", 900, "fallback")]):
        add(cfg, i, _step=0.5, verdict=verdict, latency_ms=lat, decider=decider)      # half an hour apart, all on the same day
    add(cfg, 24 * 3, verdict="would_ask")                                       # another day
    st = review.stats(load(cfg))
    assert st["total"] == 5 and st["busiest_day"] == 3 and st["flagged_per_day"] == {"2026-09-14": 3, "2026-09-17": 1}
    assert st["by_decider"] == {"jev": 3, "fast_path": 1, "fallback": 1} and st["fallback_rate_pct"] == 20.0
    assert st["latency_ms"]["max"] == 900 and st["span_days"] == 3.0 and st["configs_seen"]["wording"] == ["v2"]
    assert review.stats([])["total"] == 0


# ---- marks ---------------------------------------------------------------------------------------------------------
def test_marks_import_validates_keeps_the_latest_and_stays_private(cfg):
    add(cfg, 0); add(cfg, 1)
    a, b = (r["entry"] for r in load(cfg))
    known = {a, b}
    result = review.import_marks(cfg.state_dir, [{"entry": a, "mark": "dangerous"}, {"entry": "nope", "mark": "routine"}, {"entry": b, "mark": "maybe"}, 7], known)
    assert result == {"imported": 1, "unknown_entries": 1, "invalid": 2}
    review.import_marks(cfg.state_dir, [{"entry": a, "mark": "routine"}], known)
    assert review.load_marks(cfg.state_dir) == {a: "routine"}
    assert stat.S_IMODE(os.stat(review.marks_path(cfg.state_dir)).st_mode) == 0o600 and stat.S_IMODE(os.stat(review.review_dir(cfg.state_dir)).st_mode) == 0o700
    with pytest.raises(ValueError):
        review.import_marks(cfg.state_dir, {"entry": a}, known)


# ---- progress ---------------------------------------------------------------------------------------------------------
def by_name(rows):
    return {name: (status, detail) for name, status, detail in rows}


def test_progress_starts_not_yet_and_reports_each_criterion(cfg):
    empty = by_name(review.progress([], {}))
    assert empty["At least 200 real judged Bash calls"][0] == "NOT YET" and empty["Heartbeat present for every session"][0] == "NOT YET"
    assert empty["Interactive checklist run"][0] == "MANUAL" and empty["No unexplained reconcile gap"][0] == "NOT YET"
    for i in range(210):
        add(cfg, i, _step=0.5, verdict="would_ask" if i < 8 else "no_opinion", signals=sig(0.8 if i < 8 else 0.05))   # 210 calls in 4.4 days
    recs = load(cfg)
    rows = by_name(review.progress(recs, {}, {"fail": 0}))
    assert rows["At least 200 real judged Bash calls"][0] == "MET" and rows["At least 7 days of data"][0] == "NOT YET"
    assert rows["Every flagged call reviewed"][0] == "NOT YET" and rows["No unexplained reconcile gap"][0] == "MET"
    marks = {r["entry"]: "routine" for r in recs if r["verdict"] == "would_ask"}      # all 8 flagged calls are false alarms
    rows = by_name(review.progress(recs, marks, {"fail": 0}))
    assert rows["Every flagged call reviewed"][0] == "MET"
    status, detail = rows["Routine Bash calls escalated: 5% or fewer"]
    assert status == "MET" and detail.startswith("3.8%")                                    # 8 false alarms of 210


def test_progress_false_alarm_rate_misses_and_mcp(cfg):
    for i in range(100):
        add(cfg, i, verdict="would_ask" if i < 6 else "no_opinion")
    recs = load(cfg)
    marks = {r["entry"]: "routine" for r in recs[:6]}
    assert by_name(review.progress(recs, marks))["Routine Bash calls escalated: 5% or fewer"][0] == "NOT YET"       # 6% of 100
    dangerous = {recs[50]["entry"]: "dangerous"}                                                                    # an unflagged call marked dangerous
    rows = by_name(review.progress(recs, {**marks, **dangerous}))
    assert rows["No unreviewed dangerous miss"][0] == "NOT YET" and "1 call" in rows["No unreviewed dangerous miss"][1]
    assert by_name(review.progress(recs, {}))["No unreviewed dangerous miss"][0] == "MET"
    for i in range(100, 130):
        add(cfg, i, tool="mcp__x__y")
    recs = load(cfg)
    marks = {r["entry"]: "routine" for r in recs if r["tool"].startswith("mcp__")}
    assert by_name(review.progress(recs, marks))["MCP enforced only after 30 reviewed calls at 5% or fewer false alarms"][0] == "MET"


# ---- the page --------------------------------------------------------------------------------------------------------------
def test_page_contains_the_selection_and_never_raw_secrets_or_active_markup(cfg):
    add(cfg, 0, verdict="would_ask", signals=sig(0.9), prefix="curl </script><img src=x onerror=alert(1)>")
    add(cfg, 1, verdict="would_ask", decider="precheck", signals=None, prefix=None, secret_types=["known token prefix"])
    add(cfg, 2, signals=sig(0.3))
    html, payload = review.build_page(load(cfg), "2026-09-14_to_2026-09-21", 0.4)
    assert len(payload["flagged"]) == 2 and len(payload["near"]) == 1 and payload["seed"] == "jev-gate-review|2026-09-14_to_2026-09-21"
    data_part, template_part = html.split('<script id="data" type="application/json">')[1].split("</script>", 1)
    assert "</script>" not in data_part and "<\\/script>" in data_part            # the data block cannot be closed early
    assert "http://" not in template_part and "https://" not in template_part and "src=" not in template_part      # loads nothing external
    assert "textContent" in template_part and "innerHTML = '<tr>" in template_part  # rows are built from text, not from data markup


def test_page_file_is_private_and_lives_in_the_protected_state_directory(cfg):
    add(cfg, 0)
    path = review.write_page(cfg, load(cfg), "2026-09-14_to_2026-09-21")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600 and path.startswith(cfg.state_dir)
    import precheck
    assert precheck.protected_file_path(path)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_page_script_is_valid_javascript(cfg):
    add(cfg, 0)
    html, _ = review.build_page(load(cfg), "w", 0.4)
    script = re.findall(r"<script>(.*?)</script>", html, re.S)[0]
    done = subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(0,'utf8'))"], input=script, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


# ---- the command line -----------------------------------------------------------------------------------------------------
def test_cli_writes_the_page_imports_marks_and_prints_progress(cfg, capsys, tmp_path):
    now = datetime.datetime.now(UTC)
    for i in range(3):
        when = now - datetime.timedelta(hours=i + 1)
        audit.append(cfg.state_dir, {"ts": when.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "session": "s", "tool": "Bash", "prefix": "x", "signals": sig(),
                                     "verdict": "would_ask" if i == 0 else "no_opinion", "decider": "jev", "latency_ms": 5, "threshold": 0.4}, when)
    assert review.main([]) == 0
    assert "wrote" in capsys.readouterr().out and any(n.startswith("review-") for n in os.listdir(review.review_dir(cfg.state_dir)))
    entries = [r["entry"] for r in load(cfg)]
    marks = tmp_path / "marks.json"
    marks.write_text(json.dumps([{"entry": entries[-1], "mark": "routine"}]))
    assert review.main(["--import-marks", str(marks)]) == 0 and "imported 1 mark" in capsys.readouterr().out
    assert review.main(["--progress"]) == 0
    assert "Every flagged call reviewed" in capsys.readouterr().out
    assert review.main(["--import-marks", str(tmp_path / "missing.json")]) == 1


def test_cli_with_nothing_to_review_or_no_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JEV_GATE_HOME", make_home(tmp_path / "h", "trial"))
    assert review.main([]) == 0 and "no audit records" in capsys.readouterr().out
    monkeypatch.setenv("JEV_GATE_HOME", str(tmp_path / "nothing"))
    assert review.main([]) == 1 and "config problem" in capsys.readouterr().out


# ---- where the trial starts counting -----------------------------------------------------------------------------------
def test_parse_when_defaults_to_the_next_local_midnight_and_reads_dates_and_iso_times():
    now = datetime.datetime(2026, 9, 19, 17, 30, tzinfo=UTC)
    default = review.parse_when(None, now).astimezone()
    assert (default.hour, default.minute, default.second) == (0, 0, 0)
    assert 0 < (default - now).total_seconds() <= 24 * 3600 + 1                # strictly after now, within a day
    day = review.parse_when("2026-10-01", now).astimezone()
    assert (day.year, day.month, day.day, day.hour) == (2026, 10, 1, 0)
    assert review.parse_when("2026-10-01T08:00:00Z", now) == datetime.datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    with pytest.raises(ValueError):
        review.parse_when("next tuesday", now)


def test_the_latest_start_wins_history_is_kept_and_the_file_is_private(cfg):
    assert review.trial_start(cfg.state_dir) is None
    review.set_trial_start(cfg.state_dir, datetime.datetime(2026, 9, 20, 7, 0, tzinfo=UTC), now=T0)
    path = review.set_trial_start(cfg.state_dir, datetime.datetime(2026, 9, 22, 7, 0, tzinfo=UTC), now=T0)
    assert review.trial_start(cfg.state_dir) == datetime.datetime(2026, 9, 22, 7, 0, tzinfo=UTC)
    assert len(open(path).read().splitlines()) == 2                              # every change is kept
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    open(path, "a").write("garbage\n")
    assert review.trial_start(cfg.state_dir) == datetime.datetime(2026, 9, 22, 7, 0, tzinfo=UTC)


def test_progress_ignores_records_before_the_start(cfg, capsys):
    for i in range(30):                                                          # a busy build day: 30 flagged calls on day 1
        add(cfg, i * 0.1, verdict="would_ask", signals=sig(0.8), session="build")
    assert review.main(["--progress"]) == 0
    before = capsys.readouterr().out
    assert "Counting every record" in before and "30 on the busiest day" in before
    assert review.main(["--start-trial", "2026-09-16"]) == 0                     # a local midnight after the build day
    assert "30 earlier record(s) stay in the log" in capsys.readouterr().out
    for i in range(3):                                                           # then three ordinary days
        add(cfg, 3 * 24 + i, verdict="no_opinion", session="normal")
    add(cfg, 3 * 24 + 5, verdict="would_ask", signals=sig(0.8), session="normal")
    assert review.main(["--progress"]) == 0
    after = capsys.readouterr().out
    assert "Counting from 2026-09-16" in after and "30 earlier record(s) excluded" in after
    assert "MET      Busiest day within 10 would-be prompts: 1 on the busiest day" in after
    assert "4 of 200" in after                                                   # only the 4 counted records are judged calls
    assert len(load(cfg)) == 34                                                  # nothing was removed from the log


def test_start_trial_rejects_nonsense(cfg, capsys):
    assert review.main(["--start-trial", "soon"]) == 1 and "FAIL" in capsys.readouterr().out
    assert review.trial_start(cfg.state_dir) is None


def test_nothing_counted_is_never_reported_as_met():
    rows = {name: (status, detail) for name, status, detail in review.progress([], {}, {"fail": 0}, [])}
    for name in ("Busiest day within 10 would-be prompts", "Every flagged call reviewed", "Routine Bash calls escalated: 5% or fewer",
                 "No unexplained reconcile gap"):
        assert rows[name] == ("NOT YET", "no counted calls yet"), name
