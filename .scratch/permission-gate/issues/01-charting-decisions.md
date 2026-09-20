# Charting decisions (Q1–Q18)

Type: grilling
Status: resolved
Blocked by:

## Question

What are the scope, threat model, and policy decisions the whole effort stands on?

## Answer

Settled across three grilling rounds. Every recommendation was accepted.

**Scope and destination**
- Destination is a locked decision set plus a build spec, not an installed gate.
- Threat model: agent mistakes and injected instructions. The gate is a tripwire, not a security boundary.
- v1 covers Bash and `mcp__*` tools only (amended by [Seed the local pre-check](05-seed-local-pre-check.md): `Write`, `Edit` and `NotebookEdit` are also matched, for a local protected-path check only).
- Independent developer tool: follows CHI principles but writes nothing to the CHI ledger and claims no CCGF admission.

**Policy**
- Six signals: destructive; external effect; reads secrets; uploads local data; runs downloaded or unreviewed code; tampers with agent or system configuration.
- Small, justified always-escalate list in code (via the local pre-check), grown only from logged misses.
- The gate never allows and, in v1, never blocks (see ADR 0001).
- Jev failure or latency over 3 seconds returns `ask`.
- Fast path for provably local read-only commands. MCP tools are judged unless on a user-owned skip list, initially empty; the skip list file is a protected path.

**Data and privacy**
- Local pre-check escalates on secret-like content without sending anything; redaction is the backstop.
- Audit log: append-only local JSONL, 80-character redacted prefix plus hash, all signals, verdict, latency, decider, kept 90 days.
- Evidence: labeled command set from `Projects` and `Projects-chi` transcripts (not `Documents-Memory`), stored locally and permission-restricted. The user reviews every command marked dangerous and a random 10% of routine ones. Jev never labels. Redacted, reviewed commands may be sent to TypeSafe for evaluation, never any that trip the secret pattern check.

**Readiness and rollout** (the readiness bar below is superseded by [Close the evidence gap](09-close-the-evidence-gap.md))
- Ready when at least 200 real commands are tested, every dangerous one is escalated, and no more than about 5% of routine ones are.
- Prompt budget: at most 10 extra prompts per working day.
- Rollout: trial mode in `~/Projects/chi` for at least 200 judged calls or one week (whichever is later), then enforce there, then widen.

**Artifacts**
- Spec at `docs/permission-gate/SPEC.md`, one file indexing the decisions, with a list of deltas from the prototype.
- ADR: `docs/adr/0001-permission-gate-only-escalates.md`.
