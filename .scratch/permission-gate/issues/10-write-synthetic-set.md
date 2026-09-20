# Write the synthetic command set

Type: task (AFK)
Status: resolved
Blocked by:

## Question

Write the hand-authored synthetic set that [Close the evidence gap](09-close-the-evidence-gap.md) called for, so recall can be measured where real history is thin.

- About 42 Bash commands filling the per-signal gaps: uploads 14, external effect 10, tampers with config 9, reads secrets 7, runs downloaded code 2, destructive 0. Include borderline cases (routine-looking commands near each signal) so the set is not only obvious ones.
- About 30 MCP calls, roughly 10 dangerous and 20 routine or read-only, using tool names the user actually has (Schwab, Gmail, Google Drive, google_workspace). Arguments are fake; no real account, address, token or file path.
- Every entry is tagged `synthetic`, carries the signal it is meant to exercise (or `routine`), and is stored in `.scratch/permission-gate/data/synthetic.jsonl`, separate from `candidates.jsonl`, owner-only permissions.
- The set is never used to measure precision, and no synthetic entry contains a real secret. Run the same secret-pattern check over it as over the real pool.
- The agent proposes the intended label for each; the user reviews every one in [Label the command set](04-label-command-set.md).

The answer records where the file is, the counts per signal and per kind, and how many are borderline.

## Answer

**Where**: `.scratch/permission-gate/data/synthetic.jsonl` (mode 600, in the mode 700 data folder), separate from `candidates.jsonl`, plus `synthetic_summary.json` (counts only). Built by `tools/build_synthetic.py`, which asserts the counts below and runs the same secret-pattern check used on the real pool. Nothing here is ever executed; the entries are data.

Every entry carries `synthetic: true`, `intended_label`, `signal`, `borderline`, a one-line `rationale`, and `reviewed: false` until the user reviews it in [Label the command set](04-label-command-set.md). The labels are the agent's proposals.

**Counts** (84 entries)
- **Bash, dangerous, filling the per-signal gaps: 42**: uploads 14, external effect 10, tampers with config 9, reads secrets 7, runs downloaded code 2, destructive 0 (as decided).
- **Bash, borderline routine: 12**, two near each signal (for example a download-only `curl`, `head ~/.zshrc`, `npm install --save-dev`, `rm -rf __pycache__`). They probe false alarms but are never used to measure precision.
- **MCP, dangerous: 10** (external effect 4, uploads 3, destructive 2, tampers 1); **MCP, routine: 20**. 29 distinct tool names across Schwab, the Schwab options feed, Gmail, Google Drive, google_workspace, Obsidian, and Claude-in-Chrome, with placeholder ids and `example.com` addresses. The argument shapes for `google_workspace` are invented, since its real schema is unknown.
- 24 entries are marked borderline (8 of them among the dangerous ones), so the set is not only obvious cases. A few deliberately evade text matching (for example writing to agent settings through a variable path).
- Secret-pattern hits: **0**.

**Notes for later tickets**
- The set contains **no literal secrets**, on purpose. The local pre-check's literal-secret rules need their own unit tests with fake tokens; that is added to [Signal wording, evaluation and thresholds](06-signals-evaluation-thresholds.md).
- Several dangerous entries should be caught by the local pre-check before Jev (pipe-to-shell, `sudo`, writes to protected paths). Ticket 06 should report recall for the whole gate and for Jev alone on the commands that pass the pre-check.
- The 15-per-signal target assumed the real pool's heuristic counts were dangerous. Those were regex matches, not labels. If the labeling in ticket 04 finds fewer real dangerous commands, more synthetic ones will be needed.
