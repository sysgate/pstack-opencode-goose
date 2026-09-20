"""The audit log: append-only, hash-chained JSON lines, one file per month (slice 4 of docs/permission-gate/SPEC.md).

Standard library only, Python 3.9+, POSIX (uses flock). The design follows gmail-mcp-local's HashChainedAuditLog: each
record carries `prev` (the previous record's `entry` hash) and its own `entry` hash, so an edit, a deletion or a
reordering inside a month's file is detectable by verify(). A whole missing file is caught by heartbeat and
reconciliation (later slices), not here.
"""
from __future__ import annotations

import datetime
import fcntl
import hashlib
import json
import os
import re
from typing import List, Optional, Tuple

GENESIS = "0" * 64
FILE_RE = re.compile(r"^audit-(\d{4})-(\d{2})\.jsonl$")


def month_file(state: str, when: Optional[datetime.datetime] = None) -> str:
    when = when or datetime.datetime.now(datetime.timezone.utc)
    return os.path.join(state, f"audit-{when:%Y-%m}.jsonl")


def canonical(record: dict) -> str:
    return json.dumps({k: v for k, v in record.items() if k != "entry"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def entry_hash(record: dict) -> str:
    return hashlib.sha256(canonical(record).encode()).hexdigest()


def _last_entry(fd: int) -> str:
    size = os.fstat(fd).st_size
    if size == 0:
        return GENESIS
    os.lseek(fd, max(0, size - 65536), os.SEEK_SET)
    tail = os.read(fd, 65536).decode(errors="replace")
    lines = [l for l in tail.split("\n") if l.strip()]
    return json.loads(lines[-1])["entry"]


def append(state: str, record: dict, when: Optional[datetime.datetime] = None) -> str:
    """Add one record. The lock covers reading the last hash and writing, so parallel hooks (subagents) keep the chain."""
    os.makedirs(state, mode=0o700, exist_ok=True)
    path = month_file(state, when)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        record = dict(record)
        record["prev"] = _last_entry(fd)
        record["entry"] = entry_hash(record)
        os.write(fd, (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode())
    finally:
        os.close(fd)  # closing releases the lock
    return path


def verify(path: str) -> Tuple[bool, int, Optional[int]]:
    """(ok, records checked, first bad line number). Checks each hash and each link."""
    prev, count = GENESIS, 0
    with open(path) as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                return False, count, number
            if record.get("prev") != prev or record.get("entry") != entry_hash(record):
                return False, count, number
            prev, count = record["entry"], count + 1
    return True, count, None


def files(state: str) -> List[str]:
    try:
        return sorted(os.path.join(state, n) for n in os.listdir(state) if FILE_RE.match(n))
    except OSError:
        return []


def prune(state: str, days: int = 90, today: Optional[datetime.date] = None, dry_run: bool = True) -> List[str]:
    """Monthly files that ended more than `days` ago. Deletes them only when dry_run is False."""
    today = today or datetime.date.today()
    old = []
    for path in files(state):
        y, m = (int(g) for g in FILE_RE.match(os.path.basename(path)).groups())
        last_day = (datetime.date(y + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1))
        if (today - last_day).days > days:
            old.append(path)
    if not dry_run:
        for path in old:
            os.remove(path)
    return old


def parse_ts(text) -> Optional[datetime.datetime]:
    """An audit or transcript timestamp such as 2026-09-19T08:12:44.512Z, as an aware UTC datetime, or None."""
    try:
        parsed = datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def records(state: str, since: Optional[datetime.datetime] = None, until: Optional[datetime.datetime] = None) -> List[dict]:
    """Every readable record in [since, until), oldest first. Malformed lines are skipped: verify() reports them."""
    out = []
    for path in files(state):
        with open(path) as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                when = parse_ts(record.get("ts"))
                if when is None or (since and when < since) or (until and when >= until):
                    continue
                out.append(record)
    out.sort(key=lambda r: r["ts"])
    return out
