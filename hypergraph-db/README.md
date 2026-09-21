# CHI hypergraph database (prototype store)

`chi_hypergraph.PROTOTYPE.sqlite3` holds the CHI Platform glossary in the real hypergraph store: 75 terms, 139 avoid entries (136 distinct words),
229 semantic objects, 267 claims (hyperedges), each backed by the exact source text it came from. It is a **separate, rebuildable
prototype file**, not the gateway's live audit ledger. Nothing here touches `chi-platform/infra/chi_agent_gateway/receipts/`.
The file is gitignored (`*.sqlite3`); the Markdown glossaries stay authoritative and this file can always be rebuilt from them.

## Which store is which (there are two)

| | **This store** (use this one) | The old throwaway prototype (do not build on it) |
|---|---|---|
| File | `hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3` | `prototype-hypergraph/glossary/chi-glossary.PROTOTYPE-rebuildable.sqlite3` |
| Built by | the real store in `chi-platform` (`app/hypergraph/`): database-enforced rules, integrity check, anchor | the throwaway `prototype-hypergraph/hypergraph.py`, whose only job was to find gaps in the doctrine |
| Glossary snapshot | 2026-09-20 (75 terms, 264 claims) | 2026-09-19 (73 terms, 256 claims, 222 objects) |
| Admitted by | a human, with a note, sealed in each receipt (`human:robert-lai`) | the loader script itself, as `sys`; **no human verification** (that rule was decided after it was built) |
| Tamper-evident | receipt chain plus the outside anchor, and a read-only integrity check | receipt chain only |
| Status | the one to prototype against | frozen; kept as the record of what the prototype found (`prototype-hypergraph/FINDINGS.md`) |

The old store also shows every claim as `ADMITTED`, which is why it is easy to mistake for verified authority. It is not: under the
accepted doctrine, extracted (tier 3) evidence is admitted only by a human. Its schema differs too (integer timestamps, no
`candidate_evidence` link), so queries written against one will not run against the other. If you see 222 objects or 256 claims, you
are looking at the old one.

## State right now: loaded and VERIFIED (all 267 claims)

All 267 claims are `ADMITTED` and assertable. Integrity is clean (1,526 receipts) and the anchor agrees.

* **264 claims**, verified 2026-09-20 by `human:robert-lai` with the note "reviewed the CHI glossaries on 2026-09-20" (recorded on the
  admission receipts, tier 3, sealed with the content hash). That run was made at Robert Lai's direction after his own attempt hit a shell
  quoting error; the name has no space (`human:robert-lai`) so it is easy to search.
* **3 claims** (receipts 1518, 1521, 1524, 2026-09-20 23:44:44 UTC): the collisions of *Fast path*, *Generative layer (System 1)* and
  *Adjudication layer (System 2)* with an **Outside usage** (the router's "fast-path / diagnostic" route in `docs/ARCHITECTURE.md`, and
  TypeSafe's "System One"). They were verified as `human:robert-lai`, but **the recorded note is just `...`**, the placeholder from the
  example command, so those receipts do not say what was reviewed. Receipts cannot be edited; to fix the record, revoke and reload those 3
  claims and verify again with a real note (a human decision).

**Source notes** (`source-notes/`): background on outside things the store points at, kept as plain Markdown and never as claims. Today:
`typesafe-system-one.md` (TypeSafe's "System One" models and Jev: what the vendor's own page says, checked against the raw page).

If a glossary changes after this, `status` reports the claim as **drift** and leaves it alone; rebuild from the sources (below), or
revoke and reload, and verify again. Verification is a human act: only a `human:NAME` can do it.

## Commands (all run from `chi-platform/infra/chi_agent_gateway`, using `../../.venv/bin/python -m ...`)

| Command | What it does |
|---|---|
| `app.hypergraph.glossary define --db DB --word Scope` | Read-only. What the store asserts about a word: definition, group, words to avoid, collisions. Only admitted claims that pass the integrity check. |
| `app.hypergraph.glossary lint --db DB --text "..."` (or `--file F`) | Read-only. Checks text against the glossary: words it says to avoid (with the term to use instead and any qualifying note) and words that mean different things in different contexts. Exit 1 if it flags anything. Reports nothing until the glossary is verified. |
| `app.hypergraph.glossary status --db DB` | Loaded / verified / admitted / drifted counts. |
| `app.hypergraph.integrity --db DB` | Read-only check that every row is still explained by the receipts. Exit 0 clean, 1 not. |
| `app.hypergraph.glossary load --db DB` | Re-run after editing a glossary: adds what is new, never changes what is loaded. |
| `app.hypergraph.glossary verify --db DB --by human:NAME --note "..."` | The human phase (above). |

If a glossary changes after it was loaded, `status` reports the claim as **drift** and leaves it alone; to change what the store
says, rebuild (below) or revoke and reload, which is a human decision.

## Using it from Python (read-only, for prototyping the application)

```python
import sqlite3
from app.hypergraph import glossary, integrity, projection

db = sqlite3.connect("file:/Users/robertlai/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3?mode=ro", uri=True)
db.row_factory = sqlite3.Row

for e in glossary.define(db, "Scope"):          # what the store may assert about a word (fails closed)
    print(e.term, e.context, e.definition, e.avoid, e.collides_with)

report = integrity.check(db)                    # is every row explained by the record?
print(report.ok, report.counts)
assertable = [p for p in projection.project(db, report) if p.assertable]   # only admitted claims that pass the check
```

The model, in tables you can query directly:

* `semantic_objects` — Term, Glossary group, Avoided alias, Avoid note, Context, Predicate, Outside usage (id, type, label, scope, meanings, state).
  An *Outside usage* is a phrase the map quotes from somewhere no glossary defines; it is never a Term and is backed only by the map's words.
* `hyperedges` + `hyperedge_members` — a claim is a `CLAIM` with roles `SUBJECT`, `PREDICATE`, `OBJECT` and an optional `CONDITION`
  (the qualifying note on an "avoid" entry). Predicates: *is defined in*, *belongs to group*, *is avoided in favour of*,
  *must not be confused with*.
* `candidate_evidence` (the gateway's table) → `evidence_records` → `hyperedge_evidence` — the source text, then the verified record,
  then its binding to the claim.
* `receipts` — the hash-chained record of every decision. Everything above is explained by it.

The same word in two contexts is two objects (the gate's *Scope* is not CCGF's *Scope*); the map's declared collisions are claims, six of them: three between two terms, and three between a term and an Outside usage.

## Rebuild from the sources

The file is disposable. To start over: delete it, then

```bash
cd ~/Projects/chi-platform/infra/chi_agent_gateway
../../.venv/bin/python -m app.hypergraph.migrations migrate --db ~/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3 --create
../../.venv/bin/python -m app.hypergraph.glossary load --db ~/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3
```

Both commands refuse the gateway's live ledger unless `--allow-live` is given, and `--create` refuses an existing file.

## Updating the glossary

The Markdown glossaries are the source of truth (`CONTEXT.md` for the permission gate, `docs/ccgf/CONTEXT.md` for CCGF); the store is loaded
from them. The steps: **edit the Markdown, plan, load, verify, check**, then commit the Markdown (the database file is gitignored).

### The web editor (add or edit an entry)

```bash
python3 ~/Projects/chi/hypergraph-db/glossary-editor/server.py        # then open http://127.0.0.1:8770/
```

It listens on this machine only. Pick an entry (or "+ New"), change it, press **Preview**, then **Save to Markdown**:

* **Preview** shows the exact diff, warnings, and what each claim is in the store: *not loaded*, *loaded, unverified*, *verified*, or
  **drift** (the text changed after it was loaded). Save stays disabled until a preview succeeds for the current form.
* **Save** rewrites that one entry block and nothing else. The result is re-read and must equal the old file with only that entry changed,
  or nothing is written; a file that changed on disk since the page loaded it is refused.
* **Load** (on the page) runs `glossary load` on the prototype database: new claims arrive as `PENDING` and nothing is admitted.
* **Verify** is a human decision and is not run from the page. Once claims are pending the page builds the command from your name and a
  note (it refuses a name with spaces and placeholder notes such as `...`); copy it and run it yourself.
* Options: `--port`, `--root` (the chi checkout), `--db` (the store). It never passes `--allow-live`.

What it does not do: **delete or rename** entries (the term is fixed once created), or record **collisions** (those are declared in
`chi-platform/.../glossary.py`). Tests: `python3 -m pytest -q hypergraph-db/glossary-editor` (only ever touches temporary copies).

### What happens to the store (the same by hand)

```bash
cd ~/Projects/chi-platform/infra/chi_agent_gateway
../../.venv/bin/python -m app.hypergraph.glossary plan                                  # dry run, touches no database
../../.venv/bin/python -m app.hypergraph.glossary load   --db ~/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3
../../.venv/bin/python -m app.hypergraph.glossary verify --db <same> --by human:YOURNAME --note "<what you actually reviewed>"
```

* A **new** term, alias or claim loads as `PENDING`; `verify` touches only what is not yet admitted.
* A **changed** claim text is reported as **drift** and left alone: the store keeps asserting the old text. There is no in-place edit; the
  prototype's fix is a full rebuild (delete the file, `migrate --create`, `load`, verify everything again; see "Rebuild from the sources").
* A term, alias or note **removed** from the Markdown is not detected: its claims stay `ADMITTED` until the store is rebuilt.

## Agent workflow: the glossary lint hook

A Claude Code **PostToolUse** hook checks the prose an agent has just written (Write, Edit, MultiEdit on `.md/.mdx/.txt/.rst` files
under `~/Projects/chi`) against the verified glossary and hands the agent a short advisory note ("`sign-off` is avoided; use
Verification"). It is registered in `.claude/settings.local.json` (personal and gitignored; your committed `settings.json` and the
jev-gate PreToolUse hook are untouched). Properties: advisory only (never blocks), quiet and fail-open (any error or an unverified
glossary means silence, errors go to `~/.local/state/chi-glossary-hook/hook.log`), read-only, checks only the new text, ignores code
blocks and the glossary's own `_Avoid_:` lines, skips the glossary sources and the change logs (`CONTEXT.md`, `CONTEXT-MAP.md`,
`MAP.md`, `project-map.md`, `.scratch/`).

```bash
cd ~/Projects/chi-platform/infra/chi_agent_gateway
../../.venv/bin/python -m app.hypergraph.glossary_hook status                 # active, or why not
../../.venv/bin/python -m app.hypergraph.glossary_hook check-file PATH.md     # what it would say about a file
```

It is active now that the glossary is verified. **Claude Code reads hooks when a session starts**, so restart the session (or review
`/hooks`) after any change. To turn it off: `CHI_GLOSSARY_HOOK=off`, or delete the `hooks` key from `.claude/settings.local.json`
(a copy of the file as it was before is kept by the session that added it). Other knobs: `CHI_GLOSSARY_COLLISIONS=1` also reports
words that mean different things in two contexts (off by default: every "scope" would trigger it), `CHI_GLOSSARY_MAX_FINDINGS`,
`CHI_GLOSSARY_ROOTS`, `CHI_GLOSSARY_DB`.

## Tamper-evidence: the anchor

Every committed write appends the receipt chain's head to a sidecar file beside the database
(`chi_hypergraph.PROTOTYPE.sqlite3.anchor.jsonl`, gitignored, mode 600). It catches someone who rewrites or truncates only the
database, which the chain alone cannot. `integrity` includes it; check it on its own with
`../../.venv/bin/python -m app.hypergraph.anchor status --db DB`. It does not stop someone who can rewrite both files: keep a copy
elsewhere if that matters. The first anchor (718 receipts) was written with `anchor sync` after the integrity check was clean.

## Limits to know while prototyping

* Nothing is asserted until a human verifies (by design); after a rebuild, verify again.
* Evidence records point at a ledger request (`gateway-ledger://request/...`), not the file; the file, its hash and the anchor are
  in the request and candidate bodies.
* A claim says "the source states this", not "this is correct" (confidence 1.0 with that note).
* The anchor lives on the same machine; it raises the bar but does not remove it (see above).
