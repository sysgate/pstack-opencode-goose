"""The Jev stage (slice 3 of docs/permission-gate/SPEC.md): one request, six yes/no questions.

Standard library only, Python 3.9+, plain HTTPS, no SDK. Any failure raises; gate.main() turns every
exception into an `ask` (fail closed) and shows only the exception TYPE, so no message here may carry
text from the command, the request or the key.
"""
from __future__ import annotations

import getpass
import json
import math
import os
import ssl
import subprocess
import urllib.error
import urllib.request
from typing import Dict

import questions

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
REQUEST_TIMEOUT_SECONDS = 2.5   # inside the gate's own 3 second deadline
MAX_INPUT_CHARS = 2000          # as evaluated; a command padded past this is a known evasion
KEYCHAIN_SERVICE = "typesafe"
SYSTEM_CA_FILE = "/etc/ssl/cert.pem"   # macOS's own bundle; a python.org build ships without CA certificates


class KeyMissing(Exception):
    pass


class JevError(Exception):
    pass


def ssl_context() -> ssl.SSLContext:
    """Normal certificate and host-name verification. If this interpreter has no CA certificates of its own (the
    python.org macOS build, until "Install Certificates" is run), use the system bundle: verification stays on."""
    context = ssl.create_default_context()
    if not context.cert_store_stats().get("x509_ca") and os.path.isfile(SYSTEM_CA_FILE):
        context.load_verify_locations(cafile=SYSTEM_CA_FILE)
    return context


def api_key() -> str:
    """TYPESAFE_API_KEY, else the macOS Keychain. JEV_GATE_NO_KEYCHAIN=1 skips the Keychain: it can only
    make the gate ask more (no key means ask), never less."""
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if key:
        return key
    if not os.environ.get("JEV_GATE_NO_KEYCHAIN"):
        try:
            done = subprocess.run(["security", "find-generic-password", "-a", getpass.getuser(), "-s", KEYCHAIN_SERVICE, "-w"],
                                  capture_output=True, text=True, timeout=1.5)
            if done.returncode == 0 and done.stdout.strip():
                return done.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    raise KeyMissing()


# ---- what leaves the machine: the caller passes text already run through sanitize.for_jev_* ------------------
def build_body(tool: str, text: str) -> dict:
    """The tool name and the already-sanitized command or input. Nothing else: no working directory, no description."""
    return {"model": MODEL, "state": {"tool": tool, "input": text[:MAX_INPUT_CHARS]},
            "questions": questions.questions()}


def post_json(url: str, body: dict, key: str, timeout: float) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"authorization": f"Bearer {key}", "content-type": "application/json", "user-agent": "jev-gate/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        raise JevError(f"http {exc.code}") from None  # `from None`: never chain a message that could echo the request
    return json.loads(payload)


def parse_answers(response: dict) -> Dict[str, float]:
    answers = response.get("answers") if isinstance(response, dict) else None
    if not isinstance(answers, dict):
        raise JevError("response has no answers")
    probs = {}
    for signal in questions.SIGNALS:
        answer = answers.get(signal)
        value = answer.get("noul") if isinstance(answer, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise JevError("invalid answer")
        probs[signal] = float(value)
    return probs


def judge(tool: str, text: str) -> Dict[str, float]:
    """One call, six probabilities. Raises on a missing key, a network or HTTP failure, or a malformed answer."""
    return parse_answers(post_json(ENDPOINT, build_body(tool, text), api_key(), REQUEST_TIMEOUT_SECONDS))
