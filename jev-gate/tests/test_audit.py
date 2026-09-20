import datetime
import json
import os
import stat
import subprocess
import sys

import audit

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAN = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)


def lines(path):
    return open(path).read().splitlines()


def test_records_chain_verify_and_the_file_is_private(tmp_path):
    state = str(tmp_path / "state")
    for i in range(5):
        path = audit.append(state, {"n": i, "tool": "Bash"}, JAN)
    assert audit.verify(path) == (True, 5, None)
    assert os.path.basename(path) == "audit-2026-01.jsonl"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600 and stat.S_IMODE(os.stat(state).st_mode) == 0o700
    first, second = (json.loads(l) for l in lines(path)[:2])
    assert first["prev"] == audit.GENESIS and second["prev"] == first["entry"]


def test_an_edit_a_deletion_and_a_reorder_are_all_detected(tmp_path):
    state = str(tmp_path)
    path = audit.append(state, {"n": 0}, JAN)
    for i in range(1, 6):
        audit.append(state, {"n": i}, JAN)
    original = lines(path)

    def rewrite(new):
        open(path, "w").write("\n".join(new) + "\n")
        return audit.verify(path)

    edited = list(original); edited[2] = original[2].replace('"n":2', '"n":9')
    assert rewrite(edited) == (False, 2, 3)
    assert rewrite(original[:2] + original[3:])[0] is False        # a record removed
    assert rewrite(original[:2] + [original[3], original[2]] + original[4:])[0] is False
    assert rewrite(original + ["garbage"])[0] is False
    assert rewrite(original) == (True, 6, None)                    # the untouched log verifies again


def test_a_new_month_starts_a_new_file_and_chain(tmp_path):
    a = audit.append(str(tmp_path), {"n": 1}, JAN)
    b = audit.append(str(tmp_path), {"n": 2}, datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc))
    assert a != b and audit.verify(a)[0] and audit.verify(b)[0]
    assert audit.files(str(tmp_path)) == sorted([a, b])
    assert json.loads(lines(b)[0])["prev"] == audit.GENESIS


def test_parallel_hooks_keep_the_chain_intact(tmp_path):
    code = ("import audit, sys, datetime\n"
            "for i in range(25): audit.append(sys.argv[1], {'who': sys.argv[2], 'i': i}, datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc))")
    procs = [subprocess.Popen([sys.executable, "-c", code, str(tmp_path), str(n)], cwd=HERE) for n in range(4)]
    assert all(p.wait(timeout=60) == 0 for p in procs)
    ok, count, bad = audit.verify(os.path.join(str(tmp_path), "audit-2026-01.jsonl"))
    assert (ok, count, bad) == (True, 100, None)


def test_prune_lists_first_and_only_deletes_when_told(tmp_path):
    for month in (1, 6, 9):
        audit.append(str(tmp_path), {"m": month}, datetime.datetime(2026, month, 5, tzinfo=datetime.timezone.utc))
    today = datetime.date(2026, 9, 19)
    old = audit.prune(str(tmp_path), 90, today)                      # dry run: January ended ~230 days ago, June ~81, so only January
    assert [os.path.basename(p) for p in old] == ["audit-2026-01.jsonl"] and len(audit.files(str(tmp_path))) == 3
    audit.prune(str(tmp_path), 90, today, dry_run=False)
    assert [os.path.basename(p) for p in audit.files(str(tmp_path))] == ["audit-2026-06.jsonl", "audit-2026-09.jsonl"]
