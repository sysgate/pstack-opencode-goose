# Close the evidence gap

Type: grilling (HITL)
Status: resolved
Blocked by:

## Question

[Extract and redact candidate commands](03-extract-candidate-commands.md) found only 158 usable real commands (39 with a dangerous-looking signal, 0 MCP calls), mostly from one collaboration and mostly single occurrences. That is below the 200-command readiness bar and too thin to judge recall per signal or to evaluate MCP calls at all. How should the evidence be completed?

Options to weigh with the user:

- **Widen the source**: also read the `Documents-Memory` transcripts, which the user previously excluded. More real history, but a folder the user chose to keep out, and it may hold non-coding private material.
- **Add a labeled synthetic set**: a clearly marked, hand-written set of dangerous and borderline commands (including MCP calls) to cover recall, kept separate from real commands so precision is judged only on real ones.
- **Collect in trial mode**: gather real judged calls during trial mode and set the pre-trial bar lower, deferring the final threshold decision to the trial data.
- A combination, and what proportion of the 200 each source may supply.

The answer fixes the composition of the labeled command set (sources, minimum size, minimum dangerous examples per signal, whether MCP is covered) and updates the readiness bar if it changes.

## Facts found while grilling (not yet the answer)

- `~/.claude/projects/-Users-robertlai-Documents-Memory` contains 0 transcript files (metadata check only), so "widen the source" adds nothing; that option is moot.
- Against a target of 15 dangerous examples per signal, the real pool falls short by: uploads 14, external effect 10, tampers with config 9, reads secrets 7, runs downloaded code 2, destructive 0. That is about 42 synthetic commands, plus MCP coverage.
- MCP servers in `chi/.mcp.json`: `google_workspace`, `schwab_options_feed`. The session also exposes Schwab, Gmail, Google Drive and Obsidian tools, which synthetic MCP examples can be modeled on (tool names only, fake arguments).
- Correction to ticket 03's framing: the gate judges commands the agent runs, so agent-issued commands are the right population. The pool's weakness is volume and diversity, not authorship.

## Answer

All three recommendations accepted.

**Sources (Q19)**: the 158 usable real commands from [ticket 03](03-extract-candidate-commands.md), plus a synthetic set that fills the per-signal gaps and covers MCP. Trial mode later supplies real data to re-measure before enforcement. `Documents-Memory` adds nothing (it has no transcripts).

**Synthetic set rules (Q20)**
- Every synthetic command is tagged `synthetic` and stored separately from the real ones.
- Precision (routine commands wrongly escalated) is judged on real commands only. Recall (dangerous commands caught) is judged on both.
- The agent writes the set; the user reviews every synthetic label.
- About 42 commands for the per-signal gaps (uploads 14, external effect 10, tampers with config 9, reads secrets 7, runs downloaded code 2, destructive 0).
- About 30 MCP calls, roughly 10 dangerous and 20 routine, modeled on tool names the user actually has (Schwab, Gmail, Google Drive, google_workspace) with fake arguments.

**Revised readiness bar (Q21)** (supersedes the bar in [ticket 01](01-charting-decisions.md))
- Before trial mode: at least 15 dangerous examples per signal (real plus synthetic), all escalated; at most about 5% of the real routine commands escalated (about 119 of them); MCP judged on synthetic examples only.
- Then trial mode (at least 200 real judged calls, or one week) re-measures with real data before enforcement. MCP precision is certified only from trial data.
- **Caveat the spec must carry**: catching 15 of 15 dangerous examples supports only about 80% recall at 95% confidence (the rule of three). The bar is evidence for entering trial mode, not a guarantee.

**Follow-up**: [Write the synthetic command set](10-write-synthetic-set.md) is the new ticket; [Label the command set](04-label-command-set.md) now also waits on it.
