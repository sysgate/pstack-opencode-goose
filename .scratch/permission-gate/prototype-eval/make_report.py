"""PROTOTYPE (throwaway): build report.html, a single self-contained page to drive thresholds by hand.

LOCAL ONLY: the page embeds the masked real commands the user approved for the evaluation.
"""
import collections
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "..", "data")
SIG = ["destructive", "external_effect", "reads_secrets", "uploads_data", "runs_downloaded", "tampers_config"]
labels = {l["id"]: l for l in map(json.loads, open(f"{D}/labels_real.jsonl"))}
masked = {e["id"]: e for e in map(json.loads, open(f"{D}/eval_masked.jsonl"))}
syn = {s["id"]: s for f in ("synthetic.jsonl", "synthetic_batch2.jsonl") for s in map(json.loads, open(f"{D}/{f}"))}

items = {}
for W in ("v1", "v2"):
    for r in map(json.loads, open(f"{D}/eval_{W}_all.jsonl")):
        it = items.setdefault(r["id"], {"i": r["id"], "s": "real" if r["set"] == "real" else "syn", "l": r["label"], "g": r["signal"],
                                        "b": bool(r["borderline"]), "loc": bool(r["local"]), "w": {}, "k": ""})
        it["w"].setdefault(W, {})[r["pass"]] = [round(r["probs"][s], 3) for s in SIG]
for i, it in items.items():
    it["w"] = {W: [it["w"][W][n] for n in (1, 2, 3)] for W in it["w"]}
    if it["s"] == "real":
        it["t"] = masked[i]["text"]; it["k"] = labels[i]["class"]
    else:
        it["t"] = ("MCP " + syn[i]["tool"] + " " if syn[i]["kind"] == "mcp" else "") + syn[i]["text"]
# real routine commands escalated by the local pre-check were never sent to Jev
for i, l in labels.items():
    if i not in items and l["proposed_label"] == "routine" and masked[i]["include_in_evaluation"]:
        items[i] = {"i": i, "s": "real", "l": "routine", "g": "routine", "b": False, "loc": True, "w": {}, "k": l["class"], "t": masked[i]["text"]}
for it in items.values():
    it["t"] = " ".join(it["t"].split())[:130]

TEMPLATE = open(os.path.join(HERE, "report_template.html")).read()
page = TEMPLATE.replace("__DATA__", json.dumps({"sig": SIG, "items": list(items.values())}).replace("</", "<\\/"))
out = os.path.join(HERE, "report.html")
os.umask(0o077)
open(out, "w").write(page)
os.chmod(out, 0o600)
c = collections.Counter((it["s"], it["l"]) for it in items.values())
print("report.html written:", dict(c), "| size KB:", round(os.path.getsize(out) / 1024))
