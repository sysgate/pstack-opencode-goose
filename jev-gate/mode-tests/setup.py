"""Builds the scratch environment for the interactive checklist (README.md). Touches nothing outside ROOT.

    python3 setup.py           # create ROOT and print the launch commands
    python3 setup.py --clean   # delete ROOT

ROOT holds a throwaway home for the gate (config in ENFORCE mode, so asks are shown), three scratch projects that
register the real gate, and an allow-rules file. Your real ~/.config/jev-gate, ~/.local/state/jev-gate and
~/Projects/chi/.claude are never read or written. ROOT is kept outside the repository because a path containing
"jev-gate" is a protected path and would make every scratch write an ask by itself.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
ROOT = os.path.realpath("/tmp/gate-checklist")


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def main():
    if "--clean" in sys.argv:
        assert os.path.basename(ROOT) == "gate-checklist"
        shutil.rmtree(ROOT, ignore_errors=True)
        print("removed", ROOT)
        return
    if os.path.exists(ROOT):
        sys.exit(f"{ROOT} exists; run `python3 setup.py --clean` first")
    home, empty = os.path.join(ROOT, "home"), os.path.join(ROOT, "empty-home")
    os.makedirs(empty)
    os.environ["JEV_GATE_HOME"] = home
    import config
    import doctor
    config.init("enforce", {"checklist": ROOT})           # a deliberate, hand-made enforce config: doctor has no switch
    # A notebook inside the protected config folder, for the NotebookEdit path-field check.
    write_json(os.path.join(home, ".config", "jev-gate", "probe.ipynb"), {
        "cells": [{"cell_type": "code", "metadata": {}, "source": ["print(1)"], "outputs": [], "execution_count": None}],
        "metadata": {}, "nbformat": 4, "nbformat_minor": 5})
    write_json(os.path.join(ROOT, "proj", ".claude", "settings.json"), doctor.settings_entry())
    broken = doctor.settings_entry()                      # the same entry with a mistyped interpreter path
    for group in broken["hooks"]["PreToolUse"] + broken["hooks"]["SessionStart"]:
        for hook in group["hooks"]:
            hook["command"] = hook["command"].replace(doctor.PINNED_PYTHON, doctor.PINNED_PYTHON + "x")
    write_json(os.path.join(ROOT, "proj-badpy", ".claude", "settings.json"), broken)
    write_json(os.path.join(ROOT, "allow.json"), {"permissions": {"allow": ["Bash(rm:*)", "Bash(mkdir:*)", "Write", "Edit"]}})
    with open(os.path.join(ROOT, "proj", "keep-me.txt"), "w") as fh:
        fh.write("harmless\n")
    print(f"""Scratch environment ready in {ROOT}

Launch commands (each in its own terminal; model choice keeps the cost to cents):

  A (gate healthy):
    cd {ROOT}/proj && JEV_GATE_HOME={home} claude --setting-sources project --settings {ROOT}/allow.json --model haiku
  B (self-check must complain: an empty home has no config):
    cd {ROOT}/proj && JEV_GATE_HOME={empty} claude --setting-sources project --model haiku
  C (mistyped interpreter path):
    cd {ROOT}/proj-badpy && JEV_GATE_HOME={home} claude --setting-sources project --model haiku

Afterwards:
  JEV_GATE_HOME={home} python3 {os.path.dirname(HERE)}/doctor.py --verify
  python3 {HERE}/setup.py --clean
""")


if __name__ == "__main__":
    main()
