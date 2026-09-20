"""PROTOTYPE: quick look at one results file. Synthetic ids only are printed (invented commands)."""
import json, sys, collections
f = sys.argv[1]; T = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
rows = [json.loads(l) for l in open(f)]
syn = [r for r in rows if r["set"] == "synthetic" and not r["error"]]
data = {json.loads(l)["id"]: json.loads(l) for fn in ("synthetic.jsonl", "synthetic_batch2.jsonl") for l in open("../data/" + fn)}
dang = [r for r in syn if r["label"] == "dangerous"]
rout = [r for r in syn if r["label"] == "routine"]
own = collections.defaultdict(lambda: [0, 0]); anyhit = 0
for r in dang:
    hit_own = r["probs"][r["signal"]] >= T
    own[r["signal"]][0] += hit_own; own[r["signal"]][1] += 1
    anyhit += any(v >= T for v in r["probs"].values())
print(f"threshold {T}: dangerous caught by ANY signal {anyhit}/{len(dang)}")
print("recall on the intended signal:", {k: f"{a}/{b}" for k, (a, b) in sorted(own.items())})
print("MISSED (no signal >= T):")
for r in dang:
    if not any(v >= T for v in r["probs"].values()):
        top = sorted(r["probs"].items(), key=lambda kv: -kv[1])[:2]
        print("  ", r["id"], r["signal"], "| top:", [(k, round(v, 2)) for k, v in top], "|", data[r["id"]]["text"][:80])
print("CAUGHT only by a different signal than intended:")
for r in dang:
    if any(v >= T for v in r["probs"].values()) and r["probs"][r["signal"]] < T:
        hits = [(k, round(v, 2)) for k, v in r["probs"].items() if v >= T]
        print("  ", r["id"], r["signal"], "| intended p =", round(r["probs"][r["signal"]], 2), "| fired:", hits)
print("ROUTINE synthetic that fire (false alarms):")
for r in rout:
    hits = [(k, round(v, 2)) for k, v in r["probs"].items() if v >= T]
    if hits: print("  ", r["id"], hits, "|", data[r["id"]]["text"][:70])
lat = sorted(r["ms"] for r in syn); print("latency ms (concurrent): p50", lat[len(lat)//2], "p95", lat[int(len(lat)*.95)], "max", lat[-1])
