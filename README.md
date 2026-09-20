# CHI

The doctrine, design record and developer tooling for the **personal CHI Platform**, a contract-governed,
assurance-native hypergraph intelligence system, and its governance framework, the **CHI Cognitive Governance
Framework (CCGF)**.

> **Generation proposes. Governance admits.**
> Model output is a candidate until it passes CCGF's admission gates. It is never evidence by itself.

This repository holds the *thinking and the guard rails*. The running gateway and the hypergraph store live in the
sibling repository [`sysgate/chi-platform`](https://github.com/sysgate/chi-platform).

## The idea in one screen

CCGF admits knowledge through five boundaries, in this order:

| Boundary | Governs |
|---|---|
| 名界 Semantic Admission | what a term means |
| 據界 Evidence Governance | what backs a claim |
| 徑界 Path Governance | whether the reasoning path holds |
| 幅界 Uncertainty Governance | how far a claim can be trusted |
| 修界 Revision Governance | contradictions, revocation and closure |

Semantic agreement precedes evidence binding. Every stage fails closed: an unproven claim stays `Pending`, `Denied`,
`Unknown` or `Conflict`, never optimistically `Admitted`.

Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`AGENTS.md`](AGENTS.md), the canonical doctrine.

## What is in here

| Path | What it is |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Canonical project instructions and doctrine for any agent working on CHI |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture: boundaries, admission state machine, evidence tiers, hypergraph, SQLite persistence |
| [`docs/ccgf/`](docs/ccgf) | CCGF vocabulary ([`CONTEXT.md`](docs/ccgf/CONTEXT.md)), ADRs, proposals and the real-store plan |
| [`docs/permission-gate/SPEC.md`](docs/permission-gate/SPEC.md), [`docs/adr/`](docs/adr) | The Jev permission gate specification and its core decision |
| [`CONTEXT-MAP.md`](CONTEXT-MAP.md), [`CONTEXT.md`](CONTEXT.md) | How the two vocabularies (CCGF hypergraph, permission gate) relate |
| [`diagrams/ccgf-chain.html`](diagrams/ccgf-chain.html) | Interactive diagram of the CCGF chain |
| `CCGF_White_Paper_…docx`, `vps_architecture.docx` | The white paper and the Verified Policy System design (Word) |
| [`jev-gate/`](jev-gate) | The permission gate: a Claude Code `PreToolUse` hook (see below) |
| [`gmail-mcp-local/`](gmail-mcp-local) | A governed, telemetry-free local Gmail MCP server |
| [`prototype-hypergraph/`](prototype-hypergraph) | Throwaway SQLite prototype that stress-tests the doctrine (findings in `FINDINGS.md`) |
| [`.scratch/`](.scratch) | Working notes and tooling behind the permission-gate design, plus a superseded prototype |
| `chi_proxy.py`, `server.txt`, `nvfp4.txt`, `goose-config.yaml.staged` | Early local-model notes and config: a FastAPI proxy on :8001 in front of a vLLM-MLX server on :8000, and a staged Goose config |
| `typesafe_example.py` | A minimal TypeSafe System One demo (not part of the gate) |

## The Jev permission gate

[`jev-gate/`](jev-gate) reviews an AI coding agent's tool calls before they run and **can only add scrutiny, never grant
permission**. It is a Claude Code `PreToolUse` hook (registered in `.claude/settings.json`) that:

1. runs local pre-check rules first (a hit asks and nothing is sent anywhere),
2. skips provably local, read-only Bash commands (no opinion, never "allow"),
3. otherwise sends a sanitized command to TypeSafe's Jev model for six yes/no judgments (destructive, external effect,
   reads secrets, uploads data, runs downloaded code, tampers config) and asks a human when any probability reaches the
   threshold.

Any error, timeout, missing key or bad config fails closed to an `ask`. Every judged call is recorded in a hash-chained
audit log. It runs in **trial mode** by default (records what it would ask, prints nothing). See
[`jev-gate/README.md`](jev-gate/README.md) and the spec for modes, the weekly review and reconciliation.

The hook entry in `.claude/settings.json` contains machine-specific absolute paths; adjust them on another machine.

## Working in this repo

- Python: standard library only for `jev-gate` (3.9+). Run its tests with:
  ```bash
  python3 -m pytest -q jev-gate/tests
  ```
  No test touches your real config, Keychain or the live API.
- `gmail-mcp-local` (Node 20+): `cd gmail-mcp-local && npm ci && npm test`. It needs your own Google OAuth setup; see its
  README.
- Agents: read [`AGENTS.md`](AGENTS.md) first (`.goosehints` and `CLAUDE.md` point to it and to `MAP.md`). `MAP.md` is a
  running file map and log of what earlier sessions learned.
- Commits: keep each one scoped to a single concern (`area: concise summary`).

## What is deliberately not here

Secrets and machine-local state are gitignored and never committed: `.env` files, `.mcp.json*`,
`.claude/settings.local.json`, credentials and tokens, all SQLite databases (including hypergraph stores), vendored
`google-cloud-sdk/` and `node_modules/`. The evaluation corpora used to tune the permission gate
(`.scratch/permission-gate/data/`) are built from real command history and stay local; the gate's tests skip cleanly
when they are absent.

## Status

Personal, private, work in progress. The doctrine is under active revision; see the `proposed-*` documents in
[`docs/ccgf/`](docs/ccgf) for decisions not yet folded in.
