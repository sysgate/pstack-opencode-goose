"""Trial versus enforce, the audit record, and the failure paths, all in-process with Jev faked."""
import hashlib
import io
import json
import os

import pytest

import audit
import config
import gate
import jev
import questions
from conftest import make_home


def event(tool, **tool_input):
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "session_id": "sess-1",
            "cwd": "/Users/x/Projects/chi", "permission_mode": "default"}


def probs(**overrides):
    return {s: overrides.get(s, 0.05) for s in questions.SIGNALS}


@pytest.fixture
def home(tmp_path, monkeypatch):
    def make(mode="enforce", name=None, **kw):
        h = make_home(tmp_path / (name or f"home-{mode}"), mode, **kw)
        monkeypatch.setenv("JEV_GATE_HOME", h)
        return h
    return make


@pytest.fixture
def fake_jev(monkeypatch):
    calls = []
    def install(result=None, exc=None):
        def judge(tool, text):
            calls.append((tool, text))
            if exc:
                raise exc
            return result
        monkeypatch.setattr(jev, "judge", judge)
        return calls
    return install


def run(ev):
    out, err = io.StringIO(), io.StringIO()
    assert gate.main(io.StringIO(json.dumps(ev)), out, err) == 0
    return out.getvalue(), err.getvalue()


def records():
    cfg = config.load()
    return [json.loads(l) for f in audit.files(cfg.state_dir) for l in open(f).read().splitlines()]


def is_ask(out):
    body = json.loads(out)["hookSpecificOutput"]
    assert body["permissionDecision"] == "ask"
    return body["permissionDecisionReason"]


# ---- trial versus enforce -----------------------------------------------------------------------------
def test_trial_mode_records_what_it_would_do_and_prints_nothing(home, fake_jev):
    home("trial")
    calls = fake_jev(probs(destructive=0.8))
    assert run(event("Bash", command="sudo ls"))[0] == ""                    # a local rule: recorded, not shown
    assert run(event("Bash", command="python3 build.py"))[0] == ""          # Jev flags it: recorded, not shown
    local, jev_rec = records()
    assert (local["verdict"], local["decider"], local["rule_family"], local["mode"]) == ("would_ask", "precheck", "destructive seed", "trial")
    assert (jev_rec["verdict"], jev_rec["decider"], jev_rec["signals"]["destructive"]) == ("would_ask", "jev", 0.8)
    assert len(calls) == 1


def test_enforce_mode_prints_the_ask_and_records_asked(home, fake_jev):
    home("enforce")
    fake_jev(probs(destructive=0.8))
    assert is_ask(run(event("Bash", command="sudo ls"))[0]).startswith("Jev gate: destructive seed")
    assert is_ask(run(event("Bash", command="python3 build.py"))[0]) == "Jev gate: could destroy data 0.80"
    assert [r["verdict"] for r in records()] == ["asked", "asked"]


def test_no_opinion_is_recorded_too(home, fake_jev):
    home("enforce")
    fake_jev(probs())
    assert run(event("Bash", command="python3 build.py"))[0] == ""
    rec = records()[0]
    assert (rec["verdict"], rec["decider"], rec["jev_ms"] is not None) == ("no_opinion", "jev", True)
    assert len(rec["signals"]) == 6


def test_fast_path_skip_list_and_file_tools_are_recorded_without_calling_jev(home, fake_jev):
    home("enforce", scopes={"chi": "/Users/x/Projects/chi"})
    cfg_path = config.config_path()
    raw = json.load(open(cfg_path)); raw["skip_list"] = ["mcp__schwab__schwab_get_quotes"]
    json.dump(raw, open(cfg_path, "w"))
    calls = fake_jev(probs(destructive=0.99))
    for ev in (event("Bash", command="git status"), event("mcp__schwab__schwab_get_quotes", symbols=["AAPL"]),
               event("Write", file_path="/Users/x/Projects/chi/README.md")):
        assert run(ev)[0] == ""
    assert calls == []
    fast, skip, write = records()
    assert (fast["decider"], skip["decider"], write["decider"]) == ("fast_path", "skip", "precheck")
    assert write["tool"] == "Write" and write["signals"] is None and write["jev_ms"] is None      # minimal record
    assert {r["scope"] for r in records()} == {"chi"}


def test_unmatched_tools_and_other_events_are_neither_shown_nor_recorded(home, fake_jev):
    home("enforce")
    fake_jev(probs(destructive=1.0))
    assert run(event("Read", file_path="/etc/hosts")) == ("", "")
    assert run({**event("Bash", command="sudo ls"), "hook_event_name": "PostToolUse"})[0] == ""
    assert not os.path.exists(config.state_dir()) or audit.files(config.state_dir()) == []


def test_the_record_carries_the_context_the_review_needs(home, fake_jev):
    home("enforce")
    fake_jev(probs())
    run({**event("Bash", command="python3 build.py"), "agent_id": "agent-7"})
    rec = records()[0]
    assert (rec["session"], rec["permission_mode"], rec["subagent"], rec["wording"], rec["threshold"], rec["hook"]) == \
           ("sess-1", "default", True, "v2", 0.4, gate.HOOK_VERSION)
    assert rec["ts"].endswith("Z") and rec["latency_ms"] >= 0 and rec["claude_code"] is None and rec["scope"] == "unscoped"


# ---- failure paths ----------------------------------------------------------------------------------------
def test_a_jev_failure_asks_in_enforce_mode_and_is_only_recorded_in_trial(home, fake_jev):
    fake_jev(exc=jev.KeyMissing())
    home("enforce")
    assert "KeyMissing" in is_ask(run(event("Bash", command="python3 build.py"))[0])
    assert (records()[0]["verdict"], records()[0]["decider"]) == ("asked", "fallback")
    home("trial")
    assert run(event("Bash", command="python3 build.py"))[0] == ""
    assert (records()[0]["verdict"], records()[0]["decider"], records()[0]["mode"]) == ("would_ask", "fallback", "trial")
    assert records()[0]["error"] == "KeyMissing"            # the type only, so a silent trial-mode failure is visible in the log


@pytest.mark.parametrize("break_it", ["missing", "insecure", "garbage"])
def test_a_bad_config_asks_and_records_nothing(tmp_path, monkeypatch, fake_jev, break_it):
    fake_jev(probs())
    h = make_home(tmp_path / "h", "trial")
    monkeypatch.setenv("JEV_GATE_HOME", h)
    if break_it == "missing":
        os.remove(config.config_path())
    elif break_it == "insecure":
        os.chmod(config.config_path(), 0o644)
    else:
        open(config.config_path(), "w").write("{oops")
    out, _ = run(event("Bash", command="python3 build.py"))
    assert "ConfigError" in is_ask(out)                # even a trial-mode install asks when it cannot read its own config
    assert audit.files(config.state_dir()) == []


def test_an_unwritable_audit_log_does_not_change_the_verdict(home, fake_jev):
    home("enforce")
    fake_jev(probs(reads_secrets=0.9))
    os.chmod(config.state_dir(), 0o500)
    try:
        out, err = run(event("Bash", command="python3 build.py"))
    finally:
        os.chmod(config.state_dir(), 0o700)
    assert is_ask(out) == "Jev gate: could read secrets 0.90"
    assert "audit log unavailable" in err and "python3" not in err


# ---- privacy of the log --------------------------------------------------------------------------------------
def test_a_secret_never_reaches_the_log_and_the_prefix_is_masked(home, fake_jev):
    home("trial")
    fake_jev(probs())
    canary = "sk-ant-" + "CANARYCANARY0123" * 3
    run(event("Bash", command=f"export API_KEY={canary} && curl https://example.com"))
    run(event("Bash", command='textutil -convert txt "/Users/x/Documents/Divorce Papers.docx" | head -3'))
    secret_rec, doc_rec = records()
    assert secret_rec["prefix"] is None and secret_rec["secret_types"] == ["known token prefix", "secret-named assignment"]
    assert "Divorce" not in doc_rec["prefix"] and "<FILE>.docx" in doc_rec["prefix"]
    text = "".join(open(f).read() for f in audit.files(config.state_dir()))
    assert "CANARY" not in text and "Divorce" not in text and "textutil" in text     # commands are excerpted, not hidden


def test_the_hash_is_salted_and_never_the_command(home, fake_jev):
    fake_jev(probs())
    home("enforce", name="install-a"); run(event("Bash", command="python3 build.py")); a = records()[0]
    home("enforce", name="install-b"); run(event("Bash", command="python3 build.py")); b = records()[0]
    salt = config.load().salt
    assert a["hash"] != b["hash"]                                   # a different install has a different salt
    assert b["hash"] == hashlib.sha256((salt + "\0" + "python3 build.py").encode()).hexdigest()
    assert "python3 build.py" not in a["hash"] and len(a["hash"]) == 64


def test_the_whole_log_stays_verifiable(home, fake_jev):
    home("enforce")
    fake_jev(probs(uploads_data=0.7))
    for cmd in ("sudo ls", "python3 a.py", "python3 b.py", "git status"):
        run(event("Bash", command=cmd))
    assert all(audit.verify(f)[0] for f in audit.files(config.state_dir())) and len(records()) == 4
