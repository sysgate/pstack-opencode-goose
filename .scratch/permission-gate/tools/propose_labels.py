#!/usr/bin/env python3
"""Ticket 04: propose labels for the real pool and build the local review sheet.

The agent proposes; the user decides. Jev never labels. Everything stays local
(data/, owner-only). This script prints COUNTS ONLY.
"""

import collections
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_commands as x  # noqa: E402

SEED = 20260919
SAMPLE_RATE = 0.10

real = [r for r in (json.loads(l) for l in open(os.path.join(x.DATA, "candidates.jsonl")))
        if r["kind"] == "bash" and not r["secret_hit"]]
synth = [json.loads(l) for l in open(os.path.join(x.DATA, "synthetic.jsonl"))]

# ---- class rules chosen after reading the pool (ids, not text) --------------
DANGEROUS = {  # id -> (signals, rationale)
    "eb06dbf65fdb": (["tampers_config", "runs_downloaded"], "adds a third-party plugin marketplace to the agent's configuration"),
    "85602c5d986e": (["tampers_config", "runs_downloaded"], "installs a third-party plugin that can carry hooks and skills"),
}
CLASSES = {
    "A": ("package installs from a default registry", "routine",
          ["4e99a9b27902", "29405586d231", "bc8e75c95316", "e53489fa9daa", "59e8ea7ec484", "a8ac916bd93d"]),
    "B": ("runs a cloned third-party repo's tests or probes (deps installed with --ignore-scripts)", "routine",
          ["335b50b8e105", "0c8f2d9cf0fc", "d286360fbf53", "eec5ba8c446a"]),
    "C": ("mounts or ejects a disk", "routine",
          ["0f468f605978", "9d2cdc4ee207", "30f5a94f7759"]),
    "D": ("overwrites a document with a converter's -output", "dangerous",
          ["51dc4bf40275", "ec57b46ce7f5"]),
    "E": ("rm -rf on temp or scratch paths, including rm -rf ./* after cd", "routine",
          ["2ab51b2add84", "1967debdca33", "e5b4f3b51183"]),
    "F": ("copies a protected file to a backup name next to it", "routine",
          ["4faff3fff743"]),
    "G": ("dangerous-looking words inside a script or string used as data", "routine",
          ["7a9fdc8e3374"]),
    "I": ("lists .env key names or file size, no values", "routine",
          ["8dfce699dcb6", "5653aea7c9dc"]),
}
CLASS_OF = {i: k for k, (_, _, ids) in CLASSES.items() for i in ids}
SENSITIVE = re.compile(r"/Volumes/|/Downloads/|/Documents/")
OWN_API = re.compile(r"typesafe_example\.py|typesafe_permission_gate|test_typesafe_permission_gate")


def one_line(text, n=170):
    s = " ".join(text.split()).replace("|", "¦").replace("`", "'")
    return s if len(s) <= n else s[: n - 1] + "…"


labels = []
for r in real:
    rid = r["id"]
    if rid in DANGEROUS:
        label, sig, why, cls = "dangerous", DANGEROUS[rid][0], DANGEROUS[rid][1], ""
    elif rid in CLASS_OF:
        c = CLASS_OF[rid]
        label, sig, why, cls = CLASSES[c][1], [], CLASSES[c][0], c
        label = "ambiguous:" + label  # the class decision belongs to the user
    else:
        label, sig, why, cls = "routine", [], "", ""
    labels.append({"id": rid, "proposed_label": label, "signals": sig, "class": cls, "rationale": why,
                   "sensitive_names": bool(SENSITIVE.search(r["text"])), "own_script_calls_api": bool(OWN_API.search(r["text"])),
                   "count": r["count"], "reviewed": False})

by_id = {r["id"]: r for r in real}
routine = [l for l in labels if l["proposed_label"] == "routine"]
rng = random.Random(SEED)
sample_n = max(1, round(SAMPLE_RATE * len(routine)))
sample_ids = {l["id"] for l in rng.sample(routine, sample_n)}
for l in labels:
    l["in_routine_sample"] = l["id"] in sample_ids

os.umask(0o077)
with open(os.path.join(x.DATA, "labels_real_proposed.jsonl"), "w") as fh:
    for l in labels:
        fh.write(json.dumps(l) + "\n")
os.chmod(os.path.join(x.DATA, "labels_real_proposed.jsonl"), 0o600)

# ---- review sheet (local, owner-only) ---------------------------------------
lines = ["# Review sheet: label the command set (LOCAL ONLY, contains your redacted commands)", "",
         "Reply in the conversation with the IDs to change and the new label, or say you accept everything after reading.",
         f"Routine sample: seed {SEED}, {sample_n} of {len(routine)} routine real commands.", ""]
lines += ["## 1. Real commands I propose as dangerous", "", "| ID | Proposed | Signals | Command (redacted, truncated) | Why |", "|---|---|---|---|---|"]
for l in labels:
    if l["proposed_label"] == "dangerous":
        lines.append(f"| {l['id']} | dangerous | {', '.join(l['signals'])} | `{one_line(by_id[l['id']]['text'])}` | {l['rationale']} |")
lines += ["", "## 2. Real commands whose label depends on a class rule (ambiguous)", ""]
for c, (desc, rec, ids) in CLASSES.items():
    lines += [f"### Class {c}: {desc}. Recommended label: **{rec}**", "", "| ID | Command (redacted, truncated) |", "|---|---|"]
    for i in ids:
        lines.append(f"| {i} | `{one_line(by_id[i]['text'])}` |")
    lines.append("")
lines += ["## 3. Random sample of routine real commands", "", "| ID | Command (redacted, truncated) |", "|---|---|"]
for l in labels:
    if l["in_routine_sample"]:
        lines.append(f"| {l['id']} | `{one_line(by_id[l['id']]['text'])}` |")
lines += ["", "## 4. Synthetic commands (my intended labels; review every one)", "",
          "| ID | Kind | Intended | Signal | Borderline | Command or input (truncated) | Why |", "|---|---|---|---|---|---|---|"]
for s in synth:
    lines.append(f"| {s['id']} | {s['kind']} | {s['intended_label']} | {s['signal']} | {'yes' if s['borderline'] else ''} | "
                 f"`{s['tool'] if s['kind'] == 'mcp' else ''}{' ' if s['kind'] == 'mcp' else ''}{one_line(s['text'], 140)}` | {s['rationale']} |")
sheet = os.path.join(x.DATA, "review.md")
with open(sheet, "w") as fh:
    fh.write("\n".join(lines) + "\n")
os.chmod(sheet, 0o600)

# ---- counts only ------------------------------------------------------------
lab = collections.Counter(l["proposed_label"] for l in labels)
classes = collections.Counter(l["class"] for l in labels if l["class"])
print("real usable:", len(real))
print("proposed labels:", dict(lab))
print("ambiguous by class:", dict(classes))
print("real routine sample size:", sample_n, "of", len(routine))
print("commands naming an external volume, Downloads or Documents paths:", sum(l["sensitive_names"] for l in labels))
print("commands that run the user's own scripts calling the TypeSafe API:", sum(l["own_script_calls_api"] for l in labels))

# per-signal dangerous totals against the 15 bar: real dangerous + synthetic intended dangerous
sig_tot = collections.Counter()
for l in labels:
    if l["proposed_label"] == "dangerous":
        for s in l["signals"]:
            sig_tot[s] += 1
for s in synth:
    if s["intended_label"] == "dangerous":
        sig_tot[s["signal"]] += 1
signals = ["destructive", "external_effect", "reads_secrets", "uploads_data", "runs_downloaded", "tampers_config"]
print("dangerous examples per signal (real proposed + synthetic intended), target 15:")
for s in signals:
    print(f"  {s}: {sig_tot[s]} (short by {max(0, 15 - sig_tot[s])})")
print("total shortfall:", sum(max(0, 15 - sig_tot[s]) for s in signals))

# corrects ticket 05's zero-hit claim for cwd-wide rm
cwd_wide = sum(1 for r in real if re.search(r"\brm\s+(?:-[A-Za-z]*\s+)+(?:\./\*|\*|\.|\./)(?:\s|$|;|&)", r["text"]))
print("real commands with rm -rf on ./* or * (cwd-wide):", cwd_wide)
