"""The gate's config and state locations (slice 4 of docs/permission-gate/SPEC.md).

Standard library only, Python 3.9+. Config: ~/.config/jev-gate/config.json (mode 600). State: ~/.local/state/jev-gate/
(mode 700). Both are protected paths, so the agent cannot flip trial to enforce by writing here. A missing, invalid
or insecure config raises ConfigError, and the gate then asks (fail closed): it is never silently quiet.

JEV_GATE_HOME replaces `~` (used by tests). Whoever sets it controls where the gate looks for its config, which is
why doctor warns when it is set.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import stat
from dataclasses import dataclass, field
from typing import Dict, Tuple

import questions

MODES = ("trial", "enforce")
DEFAULT_THRESHOLD = 0.4


class ConfigError(Exception):
    pass


@dataclass
class Config:
    mode: str = "trial"
    threshold: float = DEFAULT_THRESHOLD
    wording: str = questions.WORDING_VERSION
    salt: str = "unsalted-default"
    scopes: Dict[str, str] = field(default_factory=dict)   # name -> directory prefix
    skip_list: Tuple[str, ...] = ()                        # MCP tools the user chose not to judge
    config_dir: str = ""
    state_dir: str = ""


def home() -> str:
    return os.environ.get("JEV_GATE_HOME") or os.path.expanduser("~")


def config_dir() -> str:
    return os.path.join(home(), ".config", "jev-gate")


def state_dir() -> str:
    return os.path.join(home(), ".local", "state", "jev-gate")


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def _too_open(path: str) -> bool:
    return bool(stat.S_IMODE(os.stat(path).st_mode) & 0o077)


def load() -> Config:
    path = config_path()
    try:
        if not os.path.isfile(path):
            raise ConfigError("missing")
        if _too_open(path) or _too_open(config_dir()):
            raise ConfigError("insecure permissions")
        raw = json.load(open(path))
    except ConfigError:
        raise
    except (OSError, ValueError):
        raise ConfigError("unreadable")
    if not isinstance(raw, dict):
        raise ConfigError("not an object")
    mode, threshold = raw.get("mode"), raw.get("threshold", DEFAULT_THRESHOLD)
    if mode not in MODES:
        raise ConfigError("bad mode")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0.0 < threshold <= 1.0:
        raise ConfigError("bad threshold")
    if raw.get("wording") != questions.WORDING_VERSION:
        raise ConfigError("wording version mismatch")
    salt = raw.get("salt")
    if not isinstance(salt, str) or len(salt) < 32:
        raise ConfigError("bad salt")
    scopes, skip = raw.get("scopes", {}), raw.get("skip_list", [])
    if not isinstance(scopes, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in scopes.items()):
        raise ConfigError("bad scopes")
    if not isinstance(skip, list) or not all(isinstance(t, str) for t in skip):
        raise ConfigError("bad skip list")
    return Config(mode=mode, threshold=float(threshold), wording=raw["wording"], salt=salt, scopes=scopes,
                  skip_list=tuple(skip), config_dir=config_dir(), state_dir=state_dir())


def init(mode: str = "trial", scopes: Dict[str, str] = None) -> str:
    """Create the directories (700) and a config (600) with a fresh random salt. Refuses to overwrite."""
    path = config_path()
    if os.path.exists(path):
        raise FileExistsError("config already exists")
    for d in (config_dir(), state_dir()):
        os.makedirs(d, mode=0o700, exist_ok=True)
        os.chmod(d, 0o700)
    body = {"mode": mode, "threshold": DEFAULT_THRESHOLD, "wording": questions.WORDING_VERSION, "salt": secrets.token_hex(32),
            "scopes": scopes or {}, "skip_list": []}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(body, fh, indent=2)
    return path


def scope_for(cwd: str, cfg: Config) -> str:
    best = ""
    for name, prefix in cfg.scopes.items():
        norm = prefix.rstrip("/")
        if cwd == norm or cwd.startswith(norm + "/"):
            if len(prefix) > len(best):
                best = prefix
                found = name
    return found if best else "unscoped"


def claude_version(state: str) -> str:
    """The Claude Code version cached by doctor (the hook event does not carry it); None-like empty when unknown."""
    try:
        text = open(os.path.join(state, "claude_version.txt")).read().strip()
    except OSError:
        return ""
    return text if re.fullmatch(r"[0-9][0-9A-Za-z.\-]*", text) else ""
