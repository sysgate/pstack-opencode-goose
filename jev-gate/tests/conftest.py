import atexit
import shutil
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as _config  # noqa: E402


def make_home(path, mode="enforce", **kwargs):
    """A throwaway home with an initialized gate config. JEV_GATE_HOME is restored afterwards."""
    path = str(path)
    os.makedirs(path, exist_ok=True)
    os.chmod(path, 0o700)
    old = os.environ.get("JEV_GATE_HOME")
    os.environ["JEV_GATE_HOME"] = path
    try:
        _config.init(mode, **kwargs)
    finally:
        if old is None:
            os.environ.pop("JEV_GATE_HOME", None)
        else:
            os.environ["JEV_GATE_HOME"] = old
    return path


ENFORCE_HOME = make_home(tempfile.mkdtemp(prefix="jevgate-tests-"))
atexit.register(shutil.rmtree, ENFORCE_HOME, ignore_errors=True)   # the suite used to leave one folder per run in /tmp


@pytest.fixture(autouse=True)
def _default_home(monkeypatch):
    """Every test runs against a throwaway enforce-mode home, never the real ~/.config."""
    monkeypatch.setenv("JEV_GATE_HOME", ENFORCE_HOME)
