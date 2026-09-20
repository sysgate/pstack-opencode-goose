import json
import os
import stat

import pytest

import config
from conftest import make_home


def test_init_creates_locked_down_dirs_and_a_random_salt(tmp_path, monkeypatch):
    home = make_home(tmp_path / "h", mode="trial")
    monkeypatch.setenv("JEV_GATE_HOME", home)
    cfg = config.load()
    assert cfg.mode == "trial" and cfg.threshold == 0.4 and cfg.wording == "v2" and cfg.skip_list == ()
    assert stat.S_IMODE(os.stat(config.config_path()).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(config.config_dir()).st_mode) == 0o700 and stat.S_IMODE(os.stat(config.state_dir()).st_mode) == 0o700
    other = make_home(tmp_path / "h2")
    monkeypatch.setenv("JEV_GATE_HOME", other)
    assert config.load().salt != cfg.salt and len(cfg.salt) == 64


def test_init_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_GATE_HOME", make_home(tmp_path / "h"))
    with pytest.raises(FileExistsError):
        config.init("enforce")


def _edit(monkeypatch, tmp_path, **changes):
    monkeypatch.setenv("JEV_GATE_HOME", make_home(tmp_path / "h"))
    raw = json.load(open(config.config_path()))
    raw.update(changes)
    json.dump(raw, open(config.config_path(), "w"))


@pytest.mark.parametrize("changes", [{"mode": "off"}, {"mode": None}, {"threshold": 0}, {"threshold": 1.5}, {"threshold": True}, {"wording": "v1"},
                                     {"salt": "short"}, {"scopes": {"a": 1}}, {"scopes": []}, {"skip_list": "x"}, {"skip_list": [1]}])
def test_invalid_config_raises(tmp_path, monkeypatch, changes):
    _edit(monkeypatch, tmp_path, **changes)
    with pytest.raises(config.ConfigError):
        config.load()


def test_missing_unreadable_and_insecure_config_raise(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_GATE_HOME", str(tmp_path / "empty"))
    with pytest.raises(config.ConfigError):
        config.load()
    _edit(monkeypatch, tmp_path)
    os.chmod(config.config_path(), 0o644)
    with pytest.raises(config.ConfigError) as err:
        config.load()
    assert "insecure" in str(err.value)
    os.chmod(config.config_path(), 0o600)
    os.chmod(config.config_dir(), 0o755)
    with pytest.raises(config.ConfigError):
        config.load()
    os.chmod(config.config_dir(), 0o700)
    open(config.config_path(), "w").write("{not json")
    with pytest.raises(config.ConfigError):
        config.load()


def test_scopes_pick_the_longest_matching_prefix():
    cfg = config.Config(scopes={"projects": "/Users/x/Projects", "chi": "/Users/x/Projects/chi"})
    assert config.scope_for("/Users/x/Projects/chi/jev-gate", cfg) == "chi"
    assert config.scope_for("/Users/x/Projects/other", cfg) == "projects"
    assert config.scope_for("/Users/x/Projectsfoo", cfg) == "unscoped" and config.scope_for("", cfg) == "unscoped"


def test_claude_version_is_read_from_the_cache_only_when_it_looks_like_a_version(tmp_path):
    (tmp_path / "claude_version.txt").write_text("2.1.278\n")
    assert config.claude_version(str(tmp_path)) == "2.1.278"
    (tmp_path / "claude_version.txt").write_text("rm -rf /\n")
    assert config.claude_version(str(tmp_path)) == "" and config.claude_version(str(tmp_path / "none")) == ""
