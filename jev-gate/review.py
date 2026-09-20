#!/usr/bin/env python3
"""The weekly review (slice 5 of docs/permission-gate/SPEC.md): build a local page from the audit log, take the user's
marks back, and report progress against the exit criteria for leaving trial mode.

    python3 review.py                          # page for the last 7 days -> ~/.local/state/jev-gate/review/
    python3 review.py --since 2026-09-12 --until 2026-09-19
    python3 review.py --import-marks marks.json   # marks copied from the page: [{"entry": "...", "mark": "dangerous|routine"}]
    python3 review.py --progress               # exit-criteria progress from the log and your marks
    python3 review.py --start-trial [WHEN]     # count the trial from WHEN: YYYY-MM-DD (local midnight), an ISO time, or by default
                                               # the next local midnight. Earlier records stay in the log but stop counting.

The page shows every call the gate would have asked about, every near-threshold call (0.25 up to the threshold) and a
seeded random 10% of the rest. The seed is printed, so the sample is reproducible. It contains only the audit log's masked
prefixes, is written mode 600 inside the protected state directory, and loads nothing from the network.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import random
import statistics
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit  # noqa: E402
import config  # noqa: E402
import heartbeat  # noqa: E402

NEAR_LOW = 0.25
SAMPLE_RATE = 0.10
FLAGGED = ("would_ask", "asked")
MARKS = ("dangerous", "routine")
EXIT = {"judged_calls": 200, "days": 7, "busiest_day_prompts": 10, "false_alarm_pct": 5.0, "mcp_reviewed": 30}


def max_signal(record: dict) -> float:
    signals = record.get("signals") or {}
    return max(signals.values()) if signals else 0.0


def select(records: List[dict], seed_label: str) -> Tuple[List[dict], List[dict], List[dict], int]:
    """(flagged, near-threshold, seeded sample of the rest, size of the rest)."""
    flagged = [r for r in records if r.get("verdict") in FLAGGED]
    rest = [r for r in records if r.get("verdict") not in FLAGGED]
    near = [r for r in rest if NEAR_LOW <= max_signal(r) < float(r.get("threshold") or config.DEFAULT_THRESHOLD)]
    near_ids = {r["entry"] for r in near}
    others = [r for r in rest if r["entry"] not in near_ids]
    k = max(1, round(SAMPLE_RATE * len(others))) if others else 0
    sample = sorted(random.Random(seed_label).sample(others, k), key=lambda r: r["ts"])
    return flagged, near, sample, len(others)


def percentile(values: List[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))] if ordered else 0.0


def day_of(record: dict) -> str:
    return str(record["ts"])[:10]


def stats(records: List[dict]) -> dict:
    per_day = collections.Counter(day_of(r) for r in records if r.get("verdict") in FLAGGED)
    lat = [r["latency_ms"] for r in records if isinstance(r.get("latency_ms"), (int, float))]
    stamps = [audit.parse_ts(r["ts"]) for r in records]
    span = (max(stamps) - min(stamps)).total_seconds() / 86400 if stamps else 0.0
    return {
        "total": len(records), "span_days": round(span, 1),
        "by_tool": dict(collections.Counter(r.get("tool") for r in records)),
        "by_decider": dict(collections.Counter(r.get("decider") for r in records)),
        "by_verdict": dict(collections.Counter(r.get("verdict") for r in records)),
        "flagged_per_day": dict(sorted(per_day.items())), "busiest_day": max(per_day.values()) if per_day else 0,
        "latency_ms": {"p50": percentile(lat, .5), "p95": percentile(lat, .95), "max": max(lat) if lat else 0},
        "fallback_rate_pct": round(100 * sum(r.get("decider") == "fallback" for r in records) / len(records), 1) if records else 0.0,
        "configs_seen": {k: sorted({str(r.get(k)) for r in records}) for k in ("mode", "wording", "threshold", "hook", "claude_code")},
    }


# ---- marks -------------------------------------------------------------------------------------------------
def review_dir(state: str) -> str:
    return os.path.join(state, "review")


def marks_path(state: str) -> str:
    return os.path.join(review_dir(state), "marks.jsonl")


def load_marks(state: str) -> Dict[str, str]:
    marks: Dict[str, str] = {}
    try:
        with open(marks_path(state)) as fh:
            for line in fh:
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                if m.get("mark") in MARKS and isinstance(m.get("entry"), str):
                    marks[m["entry"]] = m["mark"]      # the latest mark for a call wins
    except OSError:
        pass
    return marks


def import_marks(state: str, incoming, known_entries) -> dict:
    if not isinstance(incoming, list):
        raise ValueError("marks must be a list")
    good, unknown, invalid = [], 0, 0
    for m in incoming:
        if not (isinstance(m, dict) and m.get("mark") in MARKS and isinstance(m.get("entry"), str)):
            invalid += 1
        elif m["entry"] not in known_entries:
            unknown += 1
        else:
            good.append(m)
    os.makedirs(review_dir(state), mode=0o700, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fd = os.open(marks_path(state), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as fh:
        for m in good:
            fh.write(json.dumps({"entry": m["entry"], "mark": m["mark"], "imported_at": stamp}, separators=(",", ":")) + "\n")
    return {"imported": len(good), "unknown_entries": unknown, "invalid": invalid}


# ---- where the trial starts counting -----------------------------------------------------------------------------
def trial_start_path(state: str) -> str:
    return os.path.join(review_dir(state), "trial-start.jsonl")


def trial_start(state: str) -> Optional[datetime.datetime]:
    """The latest recorded start of the counted trial, or None. Each change is appended, never overwritten."""
    start = None
    try:
        with open(trial_start_path(state)) as fh:
            for line in fh:
                try:
                    when = audit.parse_ts(json.loads(line).get("start"))
                except (ValueError, AttributeError):
                    continue
                start = when or start
    except OSError:
        return None
    return start


def parse_when(text: Optional[str], now: Optional[datetime.datetime] = None) -> datetime.datetime:
    """`YYYY-MM-DD` is that local midnight; an ISO time without a zone is local; nothing means the next local midnight."""
    now_local = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone()
    if not text:
        when = (now_local + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif len(text) == 10:
        when = datetime.datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=now_local.tzinfo)
    else:
        when = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=now_local.tzinfo)
    return when.astimezone(datetime.timezone.utc)


def set_trial_start(state: str, when: datetime.datetime, now: Optional[datetime.datetime] = None) -> str:
    os.makedirs(review_dir(state), mode=0o700, exist_ok=True)
    path = trial_start_path(state)
    stamp = lambda d: d.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as fh:
        os.fchmod(fh.fileno(), 0o600)
        fh.write(json.dumps({"start": stamp(when), "set_at": stamp(now or datetime.datetime.now(datetime.timezone.utc))}) + "\n")
    return path


# ---- exit-criteria progress ----------------------------------------------------------------------------------
def progress(records: List[dict], marks: Dict[str, str], reconcile_summary: Optional[dict] = None,
             heartbeats: Optional[List[dict]] = None) -> List[Tuple[str, str, str]]:
    """(criterion, MET | NOT YET | MANUAL | N/A, detail) for leaving trial mode (docs/permission-gate/SPEC.md section 7)."""
    st = stats(records)
    bash = [r for r in records if r.get("tool") == "Bash" and r.get("decider") in ("jev", "precheck")]
    mcp = [r for r in records if str(r.get("tool")).startswith("mcp__") and r.get("decider") == "jev"]
    flagged = [r for r in records if r.get("verdict") in FLAGGED]
    unreviewed = [r for r in flagged if r["entry"] not in marks]

    def rate(group):
        dangerous = sum(1 for r in group if marks.get(r["entry"]) == "dangerous")
        false = sum(1 for r in group if r.get("verdict") in FLAGGED and marks.get(r["entry"]) == "routine")
        routine = len(group) - dangerous
        return (100 * false / routine) if routine else 0.0

    rows = []
    rows.append(("At least 200 real judged Bash calls", "MET" if len(bash) >= EXIT["judged_calls"] else "NOT YET", f"{len(bash)} of {EXIT['judged_calls']}"))
    rows.append(("At least 7 days of data", "MET" if st["span_days"] >= EXIT["days"] else "NOT YET", f"{st['span_days']} days"))
    if not records:
        # Nothing counted yet: a criterion that passes only because there is nothing to fail is not evidence.
        for name in ("Busiest day within 10 would-be prompts", "Every flagged call reviewed", "Routine Bash calls escalated: 5% or fewer"):
            rows.append((name, "NOT YET", "no counted calls yet"))
    else:
        rows.append(("Busiest day within 10 would-be prompts", "MET" if st["busiest_day"] <= EXIT["busiest_day_prompts"] else "NOT YET", f"{st['busiest_day']} on the busiest day"))
        if unreviewed:
            rows.append(("Every flagged call reviewed", "NOT YET", f"{len(unreviewed)} of {len(flagged)} flagged calls have no mark"))
        else:
            rows.append(("Every flagged call reviewed", "MET", f"all {len(flagged)} flagged calls are marked"))
        pct = rate(bash)
        rows.append(("Routine Bash calls escalated: 5% or fewer", "MET" if not unreviewed and pct <= EXIT["false_alarm_pct"] else "NOT YET",
                     f"{pct:.1f}% on reviewed data" + (" (unreviewed flagged calls still count against it)" if unreviewed else "")))
    misses = [r for r in records if marks.get(r["entry"]) == "dangerous" and r.get("verdict") not in FLAGGED]
    rows.append(("No unreviewed dangerous miss", "MET" if not misses else "NOT YET", f"{len(misses)} call(s) you marked dangerous that the gate would not have escalated"))
    if reconcile_summary is None or not records:
        rows.append(("No unexplained reconcile gap", "NOT YET", "run doctor.py --reconcile" if reconcile_summary is None else "no counted calls yet"))
    else:
        rows.append(("No unexplained reconcile gap", "MET" if reconcile_summary["fail"] == 0 else "NOT YET", f"{reconcile_summary['fail']} failing session(s)"))
    if not heartbeats:
        rows.append(("Heartbeat present for every session", "NOT YET", "no heartbeat counted yet (none since the trial start, or the SessionStart self-check is not installed)"))
    else:
        first = audit.parse_ts(heartbeats[0]["ts"])
        seen = heartbeat.by_session(heartbeats)
        sessions = {str(r.get("session")) for r in records if (audit.parse_ts(r["ts"]) or first) >= first and r.get("session")}
        missing = sorted(s for s in sessions if s not in seen)
        failed = sorted(s for s in sessions if s in seen and not any(b.get("ok") for b in seen[s]))
        detail = f"{len(sessions) - len(missing) - len(failed)} of {len(sessions)} sessions since the first heartbeat have a passing one"
        if missing or failed:
            detail += f" ({len(missing)} missing, {len(failed)} failed self-check)"
        rows.append(("Heartbeat present for every session", "MET" if not missing and not failed else "NOT YET", detail))
    rows.append(("doctor is clean", "MANUAL", "run doctor.py"))
    rows.append(("Interactive checklist run", "MANUAL", "jev-gate/mode-tests/README.md"))
    mcp_reviewed = sum(1 for r in mcp if r["entry"] in marks)
    rows.append(("MCP enforced only after 30 reviewed calls at 5% or fewer false alarms",
                 "MET" if mcp_reviewed >= EXIT["mcp_reviewed"] and rate(mcp) <= EXIT["false_alarm_pct"] else "NOT YET",
                 f"{mcp_reviewed} of {EXIT['mcp_reviewed']} MCP calls reviewed; MCP stays record-only until then"))
    return rows


# ---- the page ---------------------------------------------------------------------------------------------------
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jev gate weekly review (local only)</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a63;--line:#e3e0d6;--acc:#1f5f5b;--bad:#a4332b;--good:#2a7a3b;--card:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--mut:#a09f96;--line:#33322e;--acc:#6fc0b8;--bad:#e27b70;--good:#7cc48a;--card:#1e1e1c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:20px 16px 60px}
main{max-width:1100px;margin:0 auto}h1{font-size:21px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 6px}
.warn{border:1px solid var(--bad);color:var(--bad);padding:8px 12px;border-radius:8px;font-size:13px;margin:10px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px}
.card b{display:block;font-size:20px}.card span{font-size:12px;color:var(--mut)}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mut)}
code{font:12px ui-monospace,Menlo,monospace;word-break:break-all}.scroll{overflow-x:auto}
button{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:6px 12px;cursor:pointer;font:inherit}
textarea{width:100%;height:120px;font:12px ui-monospace,Menlo,monospace;background:var(--card);color:var(--fg);border:1px solid var(--line)}
label{margin-right:8px;white-space:nowrap}.mut{color:var(--mut)}
</style></head><body><main>
<h1>Weekly review of the Jev permission gate</h1>
<p class="mut" id="window"></p>
<div class="warn">LOCAL ONLY. Masked excerpts of your commands. Do not share this page.</div>
<div class="cards" id="cards"></div>
<h2>How to review</h2>
<p>Mark each call <b>dangerous</b> (the gate should have asked) or <b>routine</b> (it should not have). Flagged calls marked routine are false alarms; unflagged calls marked dangerous are misses. Then press <b>Copy marks</b>, save the text to a file and run <code>python3 review.py --import-marks FILE</code>. Marks are also kept in this browser.</p>
<div id="sections"></div>
<h2>Your marks</h2>
<button id="copy">Copy marks</button> <span class="mut" id="copied"></span>
<textarea id="out" readonly placeholder="Marks appear here as JSON"></textarea>
<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const KEY = 'jevgate-review-' + D.window;
let marks = {}; try { marks = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
const $ = id => document.getElementById(id);
$('window').textContent = D.window + ' | sample seed: ' + D.seed + ' | ' + D.stats.total + ' calls';
const st = D.stats;
[['Calls', st.total], ['Would have asked', (st.by_verdict.would_ask || 0) + (st.by_verdict.asked || 0)], ['Busiest day', st.busiest_day],
 ['Latency p95 (ms)', st.latency_ms.p95], ['Fallback rate', st.fallback_rate_pct + '%'], ['Days covered', st.span_days]].forEach(([k, v]) => {
  const c = document.createElement('div'); c.className = 'card'; const b = document.createElement('b'); b.textContent = v; const s = document.createElement('span'); s.textContent = k; c.append(b, s); $('cards').append(c); });
function refresh() { const list = Object.keys(marks).map(e => ({entry: e, mark: marks[e]})); $('out').value = JSON.stringify(list, null, 1); localStorage.setItem(KEY, JSON.stringify(marks)); }
function section(title, note, rows) {
  const h = document.createElement('h2'); h.textContent = title + ' (' + rows.length + ')'; $('sections').append(h);
  if (note) { const p = document.createElement('p'); p.className = 'mut'; p.textContent = note; $('sections').append(p); }
  const wrap = document.createElement('div'); wrap.className = 'scroll'; const t = document.createElement('table');
  t.innerHTML = '<tr><th>Time (UTC)</th><th>Tool</th><th>Signals at or above 0.25</th><th>Masked excerpt</th><th>Mark</th></tr>';
  rows.forEach(r => {
    const tr = document.createElement('tr');
    const cell = txt => { const td = document.createElement('td'); td.textContent = txt; tr.append(td); return td; };
    cell(r.ts.replace('T', ' ').slice(0, 19)); cell(r.tool);
    cell(r.signals ? Object.entries(r.signals).filter(([, v]) => v >= 0.25).sort((a, b) => b[1] - a[1]).map(([k, v]) => k + ' ' + v.toFixed(2)).join(', ') || 'none' : (r.rule_family || r.decider));
    const td = document.createElement('td'); const code = document.createElement('code'); code.textContent = r.prefix === null ? '[secret pattern: ' + (r.secret_types || []).join(', ') + ']' : r.prefix; td.append(code); tr.append(td);
    const m = document.createElement('td');
    MARKS.forEach(v => { const l = document.createElement('label'); const i = document.createElement('input'); i.type = 'radio'; i.name = r.entry; i.checked = marks[r.entry] === v;
      i.onchange = () => { marks[r.entry] = v; refresh(); }; l.append(i, ' ' + v); m.append(l); });
    tr.append(m); t.append(tr); });
  wrap.append(t); $('sections').append(wrap);
}
const MARKS = ['dangerous', 'routine'];
section('Flagged: the gate would have asked', 'Every one of these needs a mark.', D.flagged);
section('Near the threshold', 'Highest signal from 0.25 up to the threshold: the calls most likely to be misses.', D.near);
section('Random sample of the rest', 'Seeded 10% of ' + D.rest_size + ' other calls.', D.sample);
$('copy').onclick = async () => { refresh(); try { await navigator.clipboard.writeText($('out').value); $('copied').textContent = 'copied'; } catch (e) { $('out').select(); $('copied').textContent = 'select and copy manually'; } };
refresh();
</script></main></body></html>
"""


def build_page(records: List[dict], window: str, threshold: float) -> Tuple[str, dict]:
    seed = f"jev-gate-review|{window}"
    flagged, near, sample, rest_size = select(records, seed)
    keep = ("entry", "ts", "tool", "prefix", "secret_types", "signals", "verdict", "decider", "rule_family")
    slim = lambda rows: [{k: r.get(k) for k in keep} for r in rows]
    payload = {"window": window, "seed": seed, "stats": stats(records), "flagged": slim(flagged), "near": slim(near),
               "sample": slim(sample), "rest_size": rest_size, "threshold": threshold}
    return PAGE.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")), payload


def write_page(cfg, records: List[dict], window: str) -> str:
    html, _ = build_page(records, window, cfg.threshold)
    os.makedirs(review_dir(cfg.state_dir), mode=0o700, exist_ok=True)
    path = os.path.join(review_dir(cfg.state_dir), f"review-{window.replace(' ', '_').replace('/', '-')}.html")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(html)
    return path


def parse_day(text: str) -> datetime.datetime:
    return datetime.datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="first day, YYYY-MM-DD (default: 7 days ago)")
    ap.add_argument("--until", help="day after the last, YYYY-MM-DD (default: now)")
    ap.add_argument("--import-marks", metavar="FILE", help="import marks copied from the page")
    ap.add_argument("--progress", action="store_true", help="print exit-criteria progress")
    ap.add_argument("--start-trial", nargs="?", const="", metavar="WHEN",
                    help="count the trial from WHEN (YYYY-MM-DD local, or an ISO time); default: the next local midnight")
    a = ap.parse_args(argv)
    try:
        cfg = config.load()
    except config.ConfigError as exc:
        print(f"FAIL  config problem ({exc}); run doctor.py --init")
        return 1
    now = datetime.datetime.now(datetime.timezone.utc)
    since = parse_day(a.since) if a.since else now - datetime.timedelta(days=7)
    until = parse_day(a.until) if a.until else None
    if a.import_marks:
        try:
            result = import_marks(cfg.state_dir, json.load(open(a.import_marks)), {r["entry"] for r in audit.records(cfg.state_dir)})
        except (OSError, ValueError) as exc:
            print(f"FAIL  could not read the marks file ({type(exc).__name__})")
            return 1
        print(f"imported {result['imported']} mark(s); {result['unknown_entries']} unknown call(s) ignored; {result['invalid']} invalid entr(ies) ignored")
        return 0
    if a.start_trial is not None:
        try:
            when = parse_when(a.start_trial or None)
        except ValueError:
            print("FAIL  WHEN must be YYYY-MM-DD or an ISO time")
            return 1
        set_trial_start(cfg.state_dir, when)
        before = sum(1 for r in audit.records(cfg.state_dir) if (audit.parse_ts(r["ts"]) or when) < when)
        print(f"counting the trial from {when.astimezone():%Y-%m-%d %H:%M %Z} ({when:%Y-%m-%dT%H:%M:%SZ}); {before} earlier record(s) stay in the log but no longer count")
        return 0
    if a.progress:
        import reconcile
        start = trial_start(cfg.state_dir)
        records, beats = audit.records(cfg.state_dir), heartbeat.records(cfg.state_dir)
        if start:
            print(f"Counting from {start.astimezone():%Y-%m-%d %H:%M %Z}; {sum(1 for r in records if audit.parse_ts(r['ts']) < start)} earlier record(s) excluded")
            records, beats = [r for r in records if audit.parse_ts(r["ts"]) >= start], [b for b in beats if audit.parse_ts(b["ts"]) >= start]
        else:
            print("Counting every record: no trial start set (python3 review.py --start-trial)")
        rec = reconcile.summary(reconcile.reconcile(cfg, start)) if audit.files(cfg.state_dir) else None
        for name, status, detail in progress(records, load_marks(cfg.state_dir), rec, beats):
            print(f"{status:<8} {name}: {detail}")
        return 0
    records = audit.records(cfg.state_dir, since, until)
    if not records:
        print("no audit records in that window")
        return 0
    window = f"{since:%Y-%m-%d}_to_{(until or now):%Y-%m-%d}"
    path = write_page(cfg, records, window)
    print(f"wrote {path} ({len(records)} calls); open it in a browser. Local only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
