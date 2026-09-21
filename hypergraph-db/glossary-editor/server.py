#!/usr/bin/env python3
"""A local web editor for the CHI glossary: add or edit an entry, see what it will do to the hypergraph, load the new claims.

    python3 server.py                       # http://127.0.0.1:8770/  (never listens on anything but this machine)
    python3 server.py --port 8771 --db PATH --root PATH

What it does, and deliberately does not do (see hypergraph-db/README.md, "Updating the glossary"):
  * The Markdown glossaries are the source of truth. An edit rewrites ONE entry block in CONTEXT.md or docs/ccgf/CONTEXT.md and
    nothing else; the result is parsed again and must equal the old file with only that entry changed, or nothing is written.
  * Before saving, a preview shows the diff, the loader's dry-run plan, and what each claim is in the store (new, pending,
    admitted, or DRIFT: the text changed since it was loaded).
  * "Load" runs `glossary load` on the prototype database: new claims arrive as PENDING and nothing is admitted. It never passes
    --allow-live. Verification is a human act and is NOT run here; the page only builds the command for you to run.
  * It does not delete or rename entries, and it cannot record collisions (those are declared in glossary.py).
  * The database is opened read-only by this process; only the loader subprocess writes to it.

Only the standard library plus the gateway's own glossary module (read-only use of parse and build_plan).
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATEWAY = Path(os.environ.get("CHI_GATEWAY_DIR", Path.home() / "Projects" / "chi-platform" / "infra" / "chi_agent_gateway"))
if not (GATEWAY / "app" / "hypergraph" / "glossary.py").exists():
    sys.exit(f"cannot find the gateway's glossary module under {GATEWAY}\nSet CHI_GATEWAY_DIR to chi-platform/infra/chi_agent_gateway.")
sys.path.insert(0, str(GATEWAY))
from app.hypergraph import glossary as g  # noqa: E402  (path set above)

DEFAULT_ROOT = Path.home() / "Projects" / "chi"
DEFAULT_DB = DEFAULT_ROOT / "hypergraph-db" / "chi_hypergraph.PROTOTYPE.sqlite3"
# context key -> (the loader's context label, the file, whether the file groups its entries under ### headings)
CONTEXTS = {"gate": (g.GATE, "CONTEXT.md", False), "ccgf": (g.CCGF, "docs/ccgf/CONTEXT.md", True)}
MAX_BODY = 100_000
RANK = {"drift": 0, "new": 1, "pending": 2, "other": 3, "admitted": 4, "no_db": 5}   # worst first


class EditError(Exception):
    """The request cannot be applied; .messages says why, in words for the person editing."""

    def __init__(self, messages: list[str] | str):
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        super().__init__("; ".join(self.messages))


class Conflict(EditError):
    """The file changed on disk since the page loaded it."""


# ------------------------------------------------------------------ editing the Markdown (pure)


@dataclass
class Block:
    start: int          # index of the **Term**: line
    end: int            # index one past the last non-blank line of the entry
    term: str
    group: str | None


def find_blocks(lines: list[str]) -> tuple[list[Block], dict[str, int]]:
    """The entry blocks exactly as glossary.parse finds them, and the line of each ### heading."""
    blocks, headings, group, i = [], {}, None, 0
    while i < len(lines):
        if lines[i].startswith("### "):
            group = lines[i][4:].strip()
            headings.setdefault(group, i)
        m = re.match(r"^\*\*(.+?)\*\*:\s*$", lines[i])
        if m:
            j = i + 1
            while j < len(lines) and lines[j].strip():
                j += 1
            blocks.append(Block(i, j, m.group(1), group))
            i = j
            continue
        i += 1
    return blocks, headings


def render_block(term: str, definition: str, avoid: list[tuple[str, str | None]]) -> list[str]:
    block = [f"**{term}**:", definition]
    if avoid:
        block.append("_Avoid_: " + ", ".join(word + (f" ({note})" if note else "") for word, note in avoid))
    return block


def clean_entry(p: dict, *, mode: str, has_groups: bool, existing: list[str], groups: list[str]) -> dict:
    """Validate what the form sent. Returns the normalised entry, or raises EditError with every problem found."""
    errors: list[str] = []
    term = str(p.get("term", "")).strip()
    definition = re.sub(r"\s*\n\s*", " ", str(p.get("definition", ""))).strip()
    group = (str(p.get("group") or "")).strip() or None
    if not term:
        errors.append("The term is empty.")
    elif "\n" in term or "**" in term:
        errors.append("The term must be one line and must not contain **.")
    elif mode == "add" and term.lower() in {t.lower() for t in existing}:
        errors.append(f"'{term}' already exists in this glossary; edit it instead.")
    elif mode == "edit" and term not in existing:
        errors.append(f"'{term}' is not in this glossary (the term itself cannot be renamed here).")
    if not definition:
        errors.append("The definition is empty.")
    elif definition.startswith(("### ", "_Avoid_:")) or re.match(r"^\*\*.+?\*\*:\s*$", definition):
        errors.append("The definition must be plain text: it cannot start like a heading, an _Avoid_ line or another entry.")
    if has_groups:
        if not group:
            errors.append("Choose a group (or name a new one).")
        elif "\n" in group or group.startswith("#"):
            errors.append("The group name must be one line and not start with #.")
    elif group:
        errors.append("This glossary has no groups.")
    avoid, seen = [], set()
    for row in p.get("avoid") or []:
        word, note = str(row.get("word", "")).strip(), str(row.get("note") or "").strip() or None
        if not word and not note:
            continue
        if not word:
            errors.append("An avoided word has a note but no word.")
        elif re.search(r"[,()\n]", word):
            errors.append(f"The avoided word '{word}' cannot contain a comma, parentheses or a line break.")
        elif word.lower() in seen:
            errors.append(f"The avoided word '{word}' is listed twice.")
        if note and re.search(r"[()\n]", note):
            errors.append(f"The note for '{word}' cannot contain parentheses or a line break.")
        seen.add(word.lower())
        avoid.append((word, note))
    if errors:
        raise EditError(errors)
    return {"term": term, "definition": definition, "group": group if has_groups else None, "avoid": avoid, "is_new_group": bool(has_groups and group not in groups)}


def apply_edit(text: str, entry: dict, *, mode: str) -> str:
    """Rewrite one entry block (edit) or insert a new one at the end of its group (add). Touches no other line."""
    if not text.endswith("\n"):
        text += "\n"
    lines = text.split("\n")
    blocks, headings = find_blocks(lines)
    new = render_block(entry["term"], entry["definition"], entry["avoid"])
    group = entry["group"]
    if mode == "edit":
        old = next((b for b in blocks if b.term == entry["term"]), None)
        if old is None:
            raise EditError(f"'{entry['term']}' is not in the file.")
        if old.group == group:
            lines[old.start:old.end] = new
            return "\n".join(lines)
        del lines[old.start:old.end]   # moved to another group: cut it out (and one blank line), then insert it there
        if old.start < len(lines) and lines[old.start] == "" and old.start > 0 and lines[old.start - 1] == "":
            del lines[old.start]
        blocks, headings = find_blocks(lines)
    in_group = [b for b in blocks if b.group == group]
    if in_group:
        lines[in_group[-1].end:in_group[-1].end] = ["", *new]
    elif group is not None and group in headings:
        lines[headings[group] + 1:headings[group] + 1] = ["", *new]
    elif group is not None:
        while lines and lines[-1] == "":
            lines.pop()
        lines += ["", f"### {group}", "", *new, ""]
    else:
        raise EditError("Nowhere to put the entry: the file has no entries to place it after.")
    return "\n".join(lines)


def _shape(e: dict) -> tuple:
    return (e["term"], e["definition"], tuple(e["avoid"]), e["group"])


def check_roundtrip(old_text: str, new_text: str, entry: dict, mode: str) -> None:
    """The new file must parse to the old entries with only this one changed. If not, nothing is written."""
    old, new = [_shape(e) for e in g.parse(old_text)], [_shape(e) for e in g.parse(new_text)]
    target = (entry["term"], entry["definition"], tuple(entry["avoid"]), entry["group"])
    rest_old = [e for e in old if e[0] != entry["term"]]
    rest_new = [e for e in new if e[0] != entry["term"]]
    hits = [e for e in new if e[0] == entry["term"]]
    if rest_old != rest_new or hits != [target] or len(new) != len(old) + (mode == "add"):
        raise EditError("Internal check failed: re-reading the edited file would change other entries. Nothing was written.")


# ------------------------------------------------------------------ what the store says about the claims (read-only)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def claim_states(plan, db: Path) -> list[str]:
    """One state per plan claim, the same tests glossary.status uses: new (no hyperedge), drift (a hyperedge whose evidence is for
    older text), pending, admitted, or the store's own state name."""
    if not db.exists():
        return ["no_db"] * len(plan.claims)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        out = []
        for claim in plan.claims:
            hid, cid = g._hyperedge_id(plan, claim), g.candidate_id(claim)
            h = conn.execute("SELECT admission_state FROM hyperedges WHERE id = ?", (hid,)).fetchone()
            if h is None:
                out.append("new")
            elif conn.execute("SELECT 1 FROM candidate_evidence WHERE id = ?", (cid,)).fetchone() is None:
                out.append("drift")
            else:
                out.append({"ADMITTED": "admitted", "PENDING": "pending"}.get(h["admission_state"], "other"))
        return out
    except sqlite3.Error:
        return ["no_db"] * len(plan.claims)
    finally:
        conn.close()


def summarise(states: list[str]) -> dict:
    return {"claims": len(states), **{k: states.count(k) for k in ("admitted", "pending", "new", "drift", "other", "no_db")}}


def plan_with(root: Path, ctx: str | None = None, new_text: str | None = None):
    """The loader's plan for the sources under ROOT, with one glossary optionally replaced by NEW_TEXT (nothing is written).
    The real paths are kept because ids in the store derive from them. Raises glossary.GlossaryError if it cannot be planned."""
    gate, ccgf, cmap = root / CONTEXTS["gate"][1], root / CONTEXTS["ccgf"][1], root / "CONTEXT-MAP.md"
    overrides = {str(root / CONTEXTS[ctx][1]): new_text} if ctx and new_text is not None else None
    return g.build_plan(gate, ccgf, cmap, overrides=overrides)


def entry_claim_states(plan, states: list[str]) -> dict[tuple[str, str], list[dict]]:
    """(context label, term) -> [{anchor, state}] for every claim that names the term."""
    out: dict[tuple[str, str], list[dict]] = {}
    for claim, state in zip(plan.claims, states):
        for kind, scope, label in (claim.subject, claim.target):
            if kind == "Term":
                out.setdefault((scope, label), []).append({"anchor": claim.anchor, "state": state})
    return out


# ------------------------------------------------------------------ the operations the page calls


class Editor:
    def __init__(self, root: Path, db: Path):
        self.root, self.db = Path(root), Path(db)

    def _file(self, ctx: str) -> tuple[Path, str, bool]:
        if ctx not in CONTEXTS:
            raise EditError(f"Unknown glossary '{ctx}'.")
        label, rel, has_groups = CONTEXTS[ctx]
        return self.root / rel, label, has_groups

    def entries(self) -> dict:
        problems, plan, states = [], None, []
        try:
            plan = plan_with(self.root)
            states = claim_states(plan, self.db)
        except g.GlossaryError as exc:
            problems.append(str(exc))
        per_entry = entry_claim_states(plan, states) if plan else {}
        contexts, entries = {}, []
        for key, (label, rel, has_groups) in CONTEXTS.items():
            raw = (self.root / rel).read_bytes()
            parsed = g.parse(raw.decode("utf8"))
            contexts[key] = {"label": label, "file": rel, "sha": sha(raw), "has_groups": has_groups,
                             "groups": list(dict.fromkeys(e["group"] for e in parsed if e["group"]))}
            for e in parsed:
                claims = per_entry.get((label, e["term"]), [])
                worst = min((c["state"] for c in claims), key=RANK.get, default="no_db")
                entries.append({"context": key, "term": e["term"], "group": e["group"], "definition": e["definition"],
                                "avoid": [{"word": w, "note": n} for w, n in e["avoid"]], "state": worst, "claims": claims})
        return {"contexts": contexts, "entries": entries, "summary": summarise(states) if plan else None, "problems": problems,
                "db": {"path": str(self.db), "exists": self.db.exists()}}

    def prepare(self, p: dict) -> dict:
        """Everything a save would do, worked out without writing anything. Raises EditError."""
        mode = p.get("mode")
        if mode not in ("add", "edit"):
            raise EditError("mode must be add or edit.")
        path, label, has_groups = self._file(p.get("context"))
        raw = path.read_bytes()
        if p.get("base_sha") and p["base_sha"] != sha(raw):
            raise Conflict("The file changed on disk since this page loaded it. Reload the page and redo the edit.")
        text = raw.decode("utf8")
        parsed = g.parse(text)
        entry = clean_entry(p, mode=mode, has_groups=has_groups, existing=[e["term"] for e in parsed],
                            groups=list(dict.fromkeys(e["group"] for e in parsed if e["group"])))
        new_text = apply_edit(text, entry, mode=mode)
        check_roundtrip(text, new_text, entry, mode)
        try:
            plan = plan_with(self.root, p["context"], new_text)
        except g.GlossaryError as exc:
            raise EditError(f"The loader would refuse the result: {exc}")
        states = claim_states(plan, self.db)
        warnings = []
        if mode == "edit":
            old = next(e for e in parsed if e["term"] == entry["term"])
            old_avoid, new_avoid = dict(old["avoid"]), dict(entry["avoid"])
            gone = sorted(set(old_avoid) - set(new_avoid))
            noted = sorted(w for w in set(old_avoid) & set(new_avoid) if old_avoid[w] != new_avoid[w])
            if gone:
                warnings.append(f"Removed from the avoid list: {', '.join(gone)}. The store keeps asserting those claims until it is rebuilt; nothing detects a removal.")
            if noted:
                warnings.append(f"The note changed for: {', '.join(noted)}. A changed note is a NEW claim; the old one stays in the store.")
            if old["group"] != entry["group"]:
                warnings.append("The group changed. That is a new claim; the old group claim stays in the store until it is rebuilt.")
            if old["definition"] != entry["definition"]:
                warnings.append("The definition changed: its existing claim will show as DRIFT (the store still holds the old text as admitted knowledge).")
        changed = [{"anchor": c.anchor, "state": s} for c, s in zip(plan.claims, states) if s in ("new", "drift", "other")]
        diff = "\n".join(difflib.unified_diff(text.splitlines(), new_text.splitlines(), f"a/{CONTEXTS[p['context']][1]}", f"b/{CONTEXTS[p['context']][1]}", lineterm="", n=2))
        return {"entry": {**entry, "avoid": [{"word": w, "note": n} for w, n in entry["avoid"]]}, "diff": diff, "warnings": warnings,
                "changed": changed, "summary": summarise(states), "plan": plan.stats, "new_text": new_text, "path": path, "old_sha": sha(raw)}

    def preview(self, p: dict) -> dict:
        r = self.prepare(p)
        return {k: v for k, v in r.items() if k not in ("new_text", "path")}

    def save(self, p: dict) -> dict:
        r = self.prepare(p)
        tmp = r["path"].with_name(r["path"].name + ".editor-tmp")
        tmp.write_text(r["new_text"], encoding="utf8")
        os.chmod(tmp, r["path"].stat().st_mode & 0o777)
        os.replace(tmp, r["path"])   # atomic: a reader sees the old file or the new one, never half
        out = {k: v for k, v in r.items() if k not in ("new_text", "path")}
        out["saved"] = True
        return out

    def load(self) -> dict:
        """Run the loader on the prototype database: propose everything, admit nothing. Never --allow-live."""
        if not self.db.exists():
            raise EditError(f"The database {self.db} does not exist. Create it first (see hypergraph-db/README.md).")
        cmd = [sys.executable, "-m", "app.hypergraph.glossary", "load", "--db", str(self.db), "--root", str(self.root)]
        done = subprocess.run(cmd, cwd=GATEWAY, capture_output=True, text=True, timeout=180)
        return {"returncode": done.returncode, "stdout": done.stdout[-4000:], "stderr": done.stderr[-4000:]}


# ------------------------------------------------------------------ HTTP


def make_handler(editor: Editor, token: str, port: int):
    page = (HERE / "page.html").read_text(encoding="utf8").replace("__TOKEN__", token)
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{h}" for h in allowed_hosts}

    class Handler(BaseHTTPRequestHandler):
        server_version = "GlossaryEditor"

        def log_message(self, fmt, *args):
            sys.stderr.write("%s %s\n" % (self.command, self.path))

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj).encode("utf8"), "application/json; charset=utf-8")

        def _guard(self, api: bool) -> bool:
            if self.headers.get("Host", "").lower() not in allowed_hosts:      # blocks DNS rebinding
                self._json(403, {"errors": ["Bad Host header."]})
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin not in allowed_origins:           # blocks another site's page calling us
                self._json(403, {"errors": ["Bad Origin."]})
                return False
            if api and not hmac.compare_digest(self.headers.get("X-Editor-Token", ""), token):
                self._json(403, {"errors": ["Missing or wrong token. Reload the page."]})
                return False
            return True

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/":
                if self._guard(False):
                    self._send(200, page.encode("utf8"), "text/html; charset=utf-8")
            elif path == "/api/entries":
                if self._guard(True):
                    try:
                        self._json(200, editor.entries())
                    except Exception as exc:  # report, never crash the server
                        self._json(500, {"errors": [f"{type(exc).__name__}: {exc}"]})
            else:
                self._json(404, {"errors": ["Not found."]})

        def do_POST(self):
            path = self.path.split("?")[0]
            if not self._guard(True):
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    return self._json(413, {"errors": ["Request too large."]})
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("body must be a JSON object")
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"errors": [f"Bad request: {exc}"]})
            routes = {"/api/preview": lambda: editor.preview(body), "/api/save": lambda: editor.save(body), "/api/load": editor.load}
            if path not in routes:
                return self._json(404, {"errors": ["Not found."]})
            try:
                self._json(200, routes[path]())
            except Conflict as exc:
                self._json(409, {"errors": exc.messages})
            except EditError as exc:
                self._json(422, {"errors": exc.messages})
            except subprocess.TimeoutExpired:
                self._json(504, {"errors": ["The loader took too long and was stopped."]})
            except Exception as exc:
                self._json(500, {"errors": [f"{type(exc).__name__}: {exc}"]})

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="the chi repository root holding the glossaries")
    ap.add_argument("--db", default=str(DEFAULT_DB), help="the prototype database to compare against and load into")
    a = ap.parse_args(argv)
    root = Path(a.root).expanduser().resolve()
    for _, rel, _ in CONTEXTS.values():
        if not (root / rel).is_file():
            sys.exit(f"missing {root / rel}")
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(Editor(root, Path(a.db).expanduser().resolve()), token, a.port))
    print(f"CHI glossary editor: http://127.0.0.1:{a.port}/   (Ctrl-C to stop)\n  sources: {root}\n  database: {a.db}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
