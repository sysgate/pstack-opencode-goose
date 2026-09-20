# CHI hypergraph database (prototype store)

`chi_hypergraph.PROTOTYPE.sqlite3` holds the CHI Platform glossary in the real hypergraph store: 75 terms, 139 avoid entries (136 distinct words),
227 semantic objects, 264 claims (hyperedges), each backed by the exact source text it came from. It is a **separate, rebuildable
prototype file**, not the gateway's live audit ledger. Nothing here touches `chi-platform/infra/chi_agent_gateway/receipts/`.
The file is gitignored (`*.sqlite3`); the Markdown glossaries stay authoritative and this file can always be rebuilt from them.

## State right now: loaded, NOT yet verified

The machine phase is done: every term and claim is proposed, and every claim's evidence is a `CANDIDATE`. Nothing is *asserted*
yet, because under the doctrine extracted (tier 3) evidence is admitted only by a human. Until you verify, `define` answers with
"(not verified yet)" and the projection marks every claim "Pending Evidence".

**Verification is your act.** When you have reviewed the glossaries, run (as yourself):

```bash
cd ~/Projects/chi-platform/infra/chi_agent_gateway
../../.venv/bin/python -m app.hypergraph.glossary verify \
  --db ~/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3 \
  --by human:YOURNAME --note "reviewed the CHI glossaries on YYYY-MM-DD"
```

It records who verified and your note on every admission receipt, binds the evidence, and puts each claim through the four
boundaries. Then every claim is `ADMITTED` and assertable.

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

* `semantic_objects` — Term, Glossary group, Avoided alias, Avoid note, Context, Predicate (id, type, label, scope, meanings, state).
* `hyperedges` + `hyperedge_members` — a claim is a `CLAIM` with roles `SUBJECT`, `PREDICATE`, `OBJECT` and an optional `CONDITION`
  (the qualifying note on an "avoid" entry). Predicates: *is defined in*, *belongs to group*, *is avoided in favour of*,
  *must not be confused with*.
* `candidate_evidence` (the gateway's table) → `evidence_records` → `hyperedge_evidence` — the source text, then the verified record,
  then its binding to the claim.
* `receipts` — the hash-chained record of every decision. Everything above is explained by it.

The same word in two contexts is two objects (the gate's *Scope* is not CCGF's *Scope*); the map's declared collisions are claims.

## Rebuild from the sources

The file is disposable. To start over: delete it, then

```bash
cd ~/Projects/chi-platform/infra/chi_agent_gateway
../../.venv/bin/python -m app.hypergraph.migrations migrate --db ~/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3 --create
../../.venv/bin/python -m app.hypergraph.glossary load --db ~/Projects/chi/hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3
```

Both commands refuse the gateway's live ledger unless `--allow-live` is given, and `--create` refuses an existing file.

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

It does nothing until you verify the glossary. **Claude Code reads hooks when a session starts**, so restart the session (or review
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

* Nothing is asserted until a human verifies (by design). Prototype against `define`/`status`, or verify first.
* Evidence records point at a ledger request (`gateway-ledger://request/...`), not the file; the file, its hash and the anchor are
  in the request and candidate bodies.
* A claim says "the source states this", not "this is correct" (confidence 1.0 with that note).
* The anchor lives on the same machine; it raises the bar but does not remove it (see above).
