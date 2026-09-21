"""Tests for the glossary editor. They only ever touch temporary COPIES of the glossaries and a temporary database.

    python3 -m pytest -q hypergraph-db/glossary-editor
"""
import json
import shutil
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import server as ed
except SystemExit as exc:   # the gateway checkout is not on this machine
    pytest.skip(str(exc), allow_module_level=True)

REAL = ed.DEFAULT_ROOT
FILES = ("CONTEXT.md", "docs/ccgf/CONTEXT.md", "CONTEXT-MAP.md")
if not all((REAL / f).is_file() for f in FILES):
    pytest.skip("the chi glossaries are not on this machine", allow_module_level=True)


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "chi"
    for f in FILES:
        (r / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REAL / f, r / f)
    return r


def text(root, rel="docs/ccgf/CONTEXT.md"):
    return (root / rel).read_text(encoding="utf8")


def entry(term="Zed term", definition="A brand new thing.", group="The hypergraph", avoid=(("zed", None),), new_group=False):
    return {"term": term, "definition": definition, "group": group, "avoid": list(avoid), "is_new_group": new_group}


# ------------------------------------------------------------------ the renderer matches the house format


@pytest.mark.parametrize("rel", ["CONTEXT.md", "docs/ccgf/CONTEXT.md"])
def test_every_real_entry_re_renders_byte_for_byte(rel):
    lines = (REAL / rel).read_text(encoding="utf8").split("\n")
    blocks, _ = ed.find_blocks(lines)
    parsed = ed.g.parse("\n".join(lines))
    assert len(blocks) == len(parsed) > 20
    for b, e in zip(blocks, parsed):
        assert lines[b.start:b.end] == ed.render_block(e["term"], e["definition"], e["avoid"]), e["term"]


# ------------------------------------------------------------------ editing the Markdown


def test_editing_an_entry_changes_only_its_own_lines(root):
    old = text(root)
    e = entry("Scope", "The operational namespace, reworded.", "The hypergraph", [("domain", None), ("tenant", None)])
    new = ed.apply_edit(old, e, mode="edit")
    old_lines, new_lines = old.split("\n"), new.split("\n")
    block = next(b for b in ed.find_blocks(old_lines)[0] if b.term == "Scope")
    assert old_lines[:block.start] == new_lines[:block.start]                       # everything before the entry is byte-identical
    assert old_lines[block.end:] == new_lines[len(new_lines) - (len(old_lines) - block.end):]   # and everything after it
    assert new_lines[block.start:block.start + 3] == ["**Scope**:", "The operational namespace, reworded.", "_Avoid_: domain, tenant"]
    ed.check_roundtrip(old, new, e, "edit")


def test_a_new_entry_goes_at_the_end_of_its_group_and_nothing_else_moves(root):
    old = text(root)
    e = entry("Zed term", group="Narrowing and admission", avoid=[("zed", "in casual speech")])
    new = ed.apply_edit(old, e, mode="add")
    entries = ed.g.parse(new)
    idx = [x["term"] for x in entries].index("Zed term")
    assert entries[idx]["group"] == "Narrowing and admission" and entries[idx - 1]["group"] == "Narrowing and admission"
    assert entries[idx + 1]["group"] == "Boundaries and the chain"
    assert new.endswith("\n") and "\n\n\n" not in new.replace(old, "")
    ed.check_roundtrip(old, new, e, "add")


def test_a_new_group_is_appended_with_its_heading(root):
    old = text(root)
    e = entry("Zed term", group="A brand new group", new_group=True)
    new = ed.apply_edit(old, e, mode="add")
    assert new.endswith("### A brand new group\n\n**Zed term**:\nA brand new thing.\n_Avoid_: zed\n")
    ed.check_roundtrip(old, new, e, "add")


def test_the_ungrouped_gate_glossary_appends_after_the_last_entry(root):
    old = text(root, "CONTEXT.md")
    e = entry("Zed term", group=None)
    new = ed.apply_edit(old, e, mode="add")
    assert new.startswith(old) and new.endswith("\n**Zed term**:\nA brand new thing.\n_Avoid_: zed\n")
    ed.check_roundtrip(old, new, e, "add")


def test_moving_an_entry_to_another_group_cuts_and_reinserts_it(root):
    old = text(root)
    e = entry("Scope", "The operational namespace.", "Boundaries and the chain", [("domain", None)])
    new = ed.apply_edit(old, e, mode="edit")
    parsed = {x["term"]: x for x in ed.g.parse(new)}
    assert parsed["Scope"]["group"] == "Boundaries and the chain" and "\n\n\n" not in new
    ed.check_roundtrip(old, new, e, "edit")


def test_an_entry_with_no_avoid_words_renders_without_an_avoid_line():
    assert ed.render_block("T", "d", []) == ["**T**:", "d"]


def test_the_roundtrip_check_refuses_an_edit_that_disturbs_another_entry(root):
    old = text(root)
    e = entry("Scope", "The operational namespace.", "The hypergraph", [("domain", None)])
    new = ed.apply_edit(old, e, mode="edit").replace("**Receipt**:", "**Receipts**:")
    with pytest.raises(ed.EditError, match="Nothing was written"):
        ed.check_roundtrip(old, new, e, "edit")


# ------------------------------------------------------------------ validating the form


def clean(**over):
    p = {"term": "Zed term", "definition": "A thing.", "group": "The hypergraph", "avoid": [{"word": "zed", "note": ""}]}
    p.update(over)
    return ed.clean_entry(p, mode=over.pop("mode", "add"), has_groups=True, existing=["Scope", "Receipt"], groups=["The hypergraph"])


@pytest.mark.parametrize("over,needle", [
    ({"term": ""}, "term is empty"), ({"term": "a **b**"}, "must not contain"), ({"term": "scope"}, "already exists"),
    ({"definition": " "}, "definition is empty"), ({"definition": "### x"}, "plain text"), ({"definition": "_Avoid_: x"}, "plain text"),
    ({"group": ""}, "Choose a group"), ({"group": "#x"}, "not start with #"),
    ({"avoid": [{"word": "a, b", "note": ""}]}, "comma"), ({"avoid": [{"word": "a(b)", "note": ""}]}, "parentheses"),
    ({"avoid": [{"word": "a", "note": "x (y)"}]}, "parentheses"), ({"avoid": [{"word": "a", "note": ""}, {"word": "A", "note": ""}]}, "listed twice"),
    ({"avoid": [{"word": "", "note": "orphan"}]}, "no word"),
])
def test_bad_input_is_refused_with_a_reason(over, needle):
    with pytest.raises(ed.EditError) as exc:
        clean(**over)
    assert needle in " ".join(exc.value.messages)


def test_the_form_is_normalised():
    e = clean(term="  Zed term ", definition="Line one\n   line two", avoid=[{"word": " zed ", "note": " casual "}, {"word": "", "note": ""}])
    assert e["definition"] == "Line one line two" and e["avoid"] == [("zed", "casual")] and e["is_new_group"] is False
    assert clean(group="Brand new")["is_new_group"] is True


def test_a_glossary_without_groups_refuses_a_group():
    with pytest.raises(ed.EditError, match="no groups"):
        ed.clean_entry({"term": "T", "definition": "d", "group": "g", "avoid": []}, mode="add", has_groups=False, existing=[], groups=[])


def test_a_term_cannot_be_renamed_in_edit_mode():
    with pytest.raises(ed.EditError, match="cannot be renamed"):
        ed.clean_entry({"term": "Scopes", "definition": "d", "group": "g", "avoid": []}, mode="edit", has_groups=True, existing=["Scope"], groups=["g"])


# ------------------------------------------------------------------ the editor against a database


@pytest.fixture
def store(tmp_path, root):
    """A scratch database loaded (and verified under a marked test identity) from the scratch copies of the glossaries."""
    db = tmp_path / "scratch.sqlite3"
    def run(*args):
        done = subprocess.run([sys.executable, "-m", *args], cwd=ed.GATEWAY, capture_output=True, text=True, timeout=180)
        assert done.returncode == 0, done.stdout + done.stderr
    run("app.hypergraph.migrations", "migrate", "--db", str(db), "--create")
    run("app.hypergraph.glossary", "load", "--db", str(db), "--root", str(root))
    run("app.hypergraph.glossary", "verify", "--db", str(db), "--root", str(root), "--by", "human:scratch-test", "--note", "scratch copy used by the editor tests")
    return db


def test_without_a_database_every_entry_says_so(root, tmp_path):
    data = ed.Editor(root, tmp_path / "nope.sqlite3").entries()
    assert data["db"]["exists"] is False and {e["state"] for e in data["entries"]} == {"no_db"} and len(data["entries"]) == 75


def test_entries_of_a_verified_store_are_all_admitted(root, store):
    data = ed.Editor(root, store).entries()
    assert data["summary"]["claims"] == 267 and data["summary"]["admitted"] == 267 and not data["problems"]
    assert {e["state"] for e in data["entries"]} == {"admitted"}
    scope = [e for e in data["entries"] if e["term"] == "Scope"]
    assert {e["context"] for e in scope} == {"gate", "ccgf"} and all(any("~" in c["anchor"] for c in e["claims"]) for e in scope)


def test_previewing_a_new_entry_shows_new_claims_and_writes_nothing(root, store):
    before = text(root)
    r = ed.Editor(root, store).preview({"mode": "add", "context": "ccgf", "term": "Zed term", "group": "The hypergraph", "definition": "A thing.", "avoid": [{"word": "zed", "note": ""}]})
    assert {c["state"] for c in r["changed"]} == {"new"} and len(r["changed"]) == 3   # definition, group, one avoid
    assert "+**Zed term**:" in r["diff"] and r["summary"]["new"] == 3 and text(root) == before


def test_editing_a_definition_shows_drift_and_warns(root, store):
    e = next(x for x in ed.Editor(root, store).entries()["entries"] if x["context"] == "ccgf" and x["term"] == "Scope")
    r = ed.Editor(root, store).preview({"mode": "edit", "context": "ccgf", "term": "Scope", "group": e["group"], "definition": "Reworded.", "avoid": e["avoid"]})
    assert [c["state"] for c in r["changed"]] == ["drift"] and r["changed"][0]["anchor"] == "Scope/definition"
    assert any("DRIFT" in w for w in r["warnings"])


def test_removing_an_avoid_word_and_changing_a_note_are_warned_about(root, store):
    e = next(x for x in ed.Editor(root, store).entries()["entries"] if x["context"] == "gate" and x["term"] == "Fail open")
    avoid = [{"word": "fail safe", "note": "a new note"}]   # drops 'default allow', adds a note to 'fail safe'
    r = ed.Editor(root, store).preview({"mode": "edit", "context": "gate", "term": "Fail open", "group": None, "definition": e["definition"], "avoid": avoid})
    assert any("default allow" in w and "keeps asserting" in w for w in r["warnings"]) and any("fail safe" in w and "NEW claim" in w for w in r["warnings"])


def test_saving_writes_the_file_atomically_and_leaves_the_database_alone(root, store):
    db_before = (store.stat().st_size, store.stat().st_mtime_ns)
    editor = ed.Editor(root, store)
    r = editor.save({"mode": "add", "context": "gate", "term": "Zed term", "group": None, "definition": "A thing.", "avoid": [{"word": "zed", "note": ""}]})
    assert r["saved"] and text(root, "CONTEXT.md").endswith("**Zed term**:\nA thing.\n_Avoid_: zed\n")
    assert not list(root.rglob("*.editor-tmp")) and (store.stat().st_size, store.stat().st_mtime_ns) == db_before
    assert editor.entries()["summary"]["new"] == 2   # its definition and its avoid claim (the gate has no groups)


def test_a_stale_page_cannot_overwrite_a_file_that_changed(root, store):
    editor = ed.Editor(root, store)
    stale = editor.entries()["contexts"]["gate"]["sha"]
    (root / "CONTEXT.md").write_text(text(root, "CONTEXT.md") + "\n", encoding="utf8")
    with pytest.raises(ed.Conflict):
        editor.save({"mode": "add", "context": "gate", "term": "Zed term", "group": None, "definition": "d", "avoid": [], "base_sha": stale})


def test_a_source_the_loader_cannot_plan_is_reported_and_nothing_is_written(root, store):
    (root / "CONTEXT-MAP.md").write_text(text(root, "CONTEXT-MAP.md").replace("*Fast path* is tool calls the gate does not judge", "changed"), encoding="utf8")
    before = text(root)
    editor = ed.Editor(root, store)
    with pytest.raises(ed.EditError, match="loader would refuse.*no longer says"):
        editor.save({"mode": "add", "context": "ccgf", "term": "Zed term", "group": "The hypergraph", "definition": "d", "avoid": []})
    assert text(root) == before
    data = editor.entries()
    assert data["summary"] is None and data["problems"] and len(data["entries"]) == 75   # shown, not hidden; entries still listed


def test_load_adds_new_claims_as_pending_and_admits_nothing(root, store):
    editor = ed.Editor(root, store)
    editor.save({"mode": "add", "context": "gate", "term": "Zed term", "group": None, "definition": "A thing.", "avoid": [{"word": "zed", "note": ""}]})
    out = editor.load()
    assert out["returncode"] == 0 and "'hyperedges': 2" in out["stdout"]
    s = editor.entries()["summary"]
    assert s["pending"] == 2 and s["new"] == 0 and s["admitted"] == 267


def test_load_refuses_a_missing_database(root, tmp_path):
    with pytest.raises(ed.EditError, match="does not exist"):
        ed.Editor(root, tmp_path / "nope.sqlite3").load()


# ------------------------------------------------------------------ the HTTP surface


@pytest.fixture
def http(root, tmp_path):
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    token = "test-token"
    srv = ThreadingHTTPServer(("127.0.0.1", port), ed.make_handler(ed.Editor(root, tmp_path / "nope.sqlite3"), token, port))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield {"url": f"http://127.0.0.1:{port}", "port": port, "token": token}
    srv.shutdown(); srv.server_close()


def call(http, path, body=None, headers=None, token=True):
    h = {"Content-Type": "application/json", **({"X-Editor-Token": http["token"]} if token else {}), **(headers or {})}
    req = urllib.request.Request(http["url"] + path, data=None if body is None else json.dumps(body).encode(), headers=h, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_the_page_is_served_with_its_token_and_a_strict_policy(http):
    with urllib.request.urlopen(http["url"] + "/") as r:
        body = r.read().decode()
        assert 'const TOKEN = "test-token"' in body and "__TOKEN__" not in body
        assert "default-src 'none'" in r.headers["Content-Security-Policy"] and r.headers["Cache-Control"] == "no-store"


def test_the_api_needs_the_token(http):
    assert call(http, "/api/entries", token=False)[0] == 403
    assert call(http, "/api/preview", {}, token=False)[0] == 403
    assert call(http, "/api/entries", headers={"X-Editor-Token": "wrong"})[0] == 403
    assert call(http, "/api/entries")[0] == 200


def test_a_foreign_host_or_origin_is_refused(http):
    assert call(http, "/api/entries", headers={"Host": "evil.example:80"})[0] == 403          # DNS rebinding
    assert call(http, "/api/preview", {}, headers={"Origin": "http://evil.example"})[0] == 403  # another site's page
    assert call(http, "/api/preview", {"mode": "add"}, headers={"Origin": f"http://127.0.0.1:{http['port']}"})[0] == 422


def test_http_status_codes_for_bad_requests(http):
    assert call(http, "/nope")[0] == 404
    assert call(http, "/api/nope", {})[0] == 404
    code, body = call(http, "/api/preview", {"mode": "add", "context": "nope"})
    assert code == 422 and "Unknown glossary" in json.loads(body)["errors"][0]
    assert call(http, "/api/preview", {"x": "y" * 200_000})[0] == 413
    req = urllib.request.Request(http["url"] + "/api/preview", data=b"not json", headers={"X-Editor-Token": http["token"]}, method="POST")
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 400


def test_a_full_preview_over_http(http):
    code, body = call(http, "/api/preview", {"mode": "add", "context": "gate", "term": "Zed term", "group": None, "definition": "d", "avoid": []})
    r = json.loads(body)
    assert code == 200 and "+**Zed term**:" in r["diff"] and "new_text" not in r and "path" not in r
