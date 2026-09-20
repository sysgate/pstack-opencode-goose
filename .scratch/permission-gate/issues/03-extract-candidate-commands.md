# Extract and redact candidate commands from transcripts

Type: task (AFK)
Status: resolved
Blocked by:

## Question

Build the pool of real commands the labeled command set will be drawn from.

- Read Bash and `mcp__*` tool calls from the transcripts under `~/.claude/projects/-Users-robertlai-Projects` and `~/.claude/projects/-Users-robertlai-Projects-chi` only. Do not read `-Users-robertlai-Documents-Memory`.
- Keep everything local, under `.scratch/permission-gate/data/`, permission-restricted. Nothing goes to TypeSafe or any other service in this ticket.
- De-duplicate; redact secret-like strings; record counts per tool and how many were dropped by redaction.
- Report how many usable commands exist, and whether there are enough dangerous-looking ones to reach the 200-command readiness bar; if not, say what is missing.

The answer records where the data lives and the counts, not the commands themselves.

## Answer

**Where**: `.scratch/permission-gate/data/candidates.jsonl` (mode 600, in a mode 700 folder) plus `extract_summary.json` (counts only). Built by `tools/extract_commands.py`; `tools/diagnose.py` explains redaction hits. Only `~/.claude/projects/-Users-robertlai-Projects` and `...-Projects-chi` were read; the extractor refuses any folder with "Memory" in its name. Nothing was sent anywhere, and no command text was printed during the run.

**Counts** (from 5 transcript files across 4 sessions, 2026-08-17 to 2026-09-19)
- 170 raw Bash calls (about a quarter from `Projects`, three quarters from `Projects-chi`), **0 MCP calls**.
- 165 unique after de-duplication; 161 of them appeared exactly once.
- 7 tripped the secret-pattern check (excluded from evaluation) and 158 are usable.
- 39 of the usable ones match at least one rough heuristic signal (destructive 19, runs downloaded code 13, reads secrets 8, tampers with config 6, external effect 5, uploads data 1). These are a feasibility count only, not labels.
- 84 rows are multi-line and 29 contain a heredoc.

**A correction worth keeping**: the first pass flagged 56 of 163 commands as secrets. 53 of those came from a generic long-token rule catching UUIDs in the scratchpad path. The rule now skips UUIDs and path segments, leaving 7 real hits. Redaction rules of this kind need a diagnosis step before their counts are trusted.

**Findings**
- **Below the bar.** 158 usable commands is under the 200 target, and 39 possible dangerous ones is thin for judging recall per signal (uploads has 1).
- **Not representative.** Almost every command occurs once, comes from four sessions, and the `Projects-chi` folder (where this conversation lives) supplies most of them. The pool mostly reflects this collaboration, not a long history of the user's own habits.
- **No MCP evidence at all**, so MCP judgments cannot be evaluated from this data.
- Adding `Documents-Memory` is the obvious source of more history, but the user excluded it.

**Consequence**: ticket 09 decides how to close the evidence gap; ticket 04 now waits on it.

## Correction (found while working [Write the second synthetic batch](11-write-second-synthetic-batch.md))

The secret-flag redaction rule falsely matched `-password` inside `security find-generic-password -s …`. Up to 3 of the 7 excluded rows may have been this false positive, so up to 3 more commands could have been usable. The rule is fixed for future runs; the pool was not regenerated, and the labels are unaffected.
