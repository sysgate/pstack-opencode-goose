# Write the second synthetic batch

Type: task (AFK, then a short user review)
Status: resolved
Blocked by:

## Question

[Label the command set](04-label-command-set.md) showed that only 4 real commands are dangerous, leaving the per-signal bar 34 dangerous examples short (destructive 11, runs downloaded code 11, reads secrets 8, tampers with config 3, external effect 1, uploads 0). Write a second tagged synthetic batch under the same rules as [Write the synthetic command set](10-write-synthetic-set.md):

- About 40 entries: at least the shortfall per signal, plus a few borderline cases (routine-looking commands near a signal, and dangerous ones that evade text matching).
- Stored in `.scratch/permission-gate/data/synthetic_batch2.jsonl`, owner-only, separate from the first batch and the real pool. Tagged `synthetic`, never executed, never used for precision, reserved example domains and placeholder ids, no literal secrets, and the same secret-pattern check.
- Intended labels are the agent's proposals and `reviewed: false`; the user reviews every entry, as with the first batch.
- Include destructive cases for both Bash and MCP tools, since the first batch had no destructive Bash.

The answer records where the file is, the per-signal counts after adding it to the real and first-batch counts, and the review outcome.

## Progress (not yet the answer): batch written, waiting for the user's review

**Where**: `data/synthetic_batch2.jsonl` (mode 600), `data/synthetic_batch2_summary.json`, and section 7 of `data/review.md`. Built by `tools/build_synthetic2.py`. Every entry is tagged `synthetic`, `batch: 2`, `reviewed: false`; never executed; reserved example domains and placeholder ids; secret-pattern hits: 0.

**Counts** (45 entries)
- 36 dangerous Bash: destructive 9, runs downloaded code 12, reads secrets 9, tampers with config 4, external effect 2; plus 3 dangerous MCP calls (all destructive: a permanent Drive delete, a spreadsheet clear, a Gmail trash). 4 of the dangerous ones are marked borderline.
- 6 borderline routine Bash (regenerable `rm -rf`, a requirements-file install, listing `~/.ssh`, a backup copy of a shell profile, reading git state, ejecting a disk).
- **Dangerous per signal after this batch** (real plus batch 1 plus batch 2), target 15: destructive 16, external effect 16, reads secrets 16, uploads 17, runs downloaded code 16, tampers with config 16. The bar is met with one entry of headroom per signal, so relabeling more than one entry per signal during review would put a signal back under 15.

**Found while building**: the extractor's secret-flag rule matched `-password` inside `security find-generic-password -s …`, a false positive. Fixed with a lookbehind so only a flag that starts a word matches (`--password x` is still caught). The real pool's extraction was not regenerated; up to 3 of its 7 excluded rows may have been this false positive, which errs on the safe side and does not affect the labels. The same lookbehind belongs in the pre-check's literal-secret rule.

## Answer

**Review outcome**: the user read section 7 of `data/review.md` and accepted every intended label ("read it and accept everything"). No entry was relabeled. All 45 entries are now `reviewed: true` in `data/synthetic_batch2.jsonl` (mode 600).

**Where**: `data/synthetic_batch2.jsonl`, with a counts-only `data/synthetic_batch2_summary.json`. Built by `tools/build_synthetic2.py`; 0 secret-pattern hits; never executed; never used for precision.

**Counts** (45 entries): 36 dangerous Bash (destructive 9, runs downloaded code 12, reads secrets 9, tampers with config 4, external effect 2), 3 dangerous MCP calls (all destructive), and 6 borderline routine Bash. 4 of the dangerous entries are borderline.

**Dangerous examples per signal** (reviewed real labels plus both batches), target 15: destructive 16, external effect 16, reads secrets 16, uploads 17, runs downloaded code 16, tampers with config 16. **The pre-trial bar in [Close the evidence gap](09-close-the-evidence-gap.md) is met**, with one entry of headroom per signal.

**What the bar does and does not show**: only 4 real commands are dangerous, so every dangerous example beyond those 4 is synthetic. Recall on real commands cannot be measured before trial mode, and the 15-of-15 caveat (about 80% recall at 95% confidence) still applies.

**Follow-up already recorded**: the secret-flag false positive is in the evaluation ticket's unit tests; the corrections are noted in [Extract and redact candidate commands](03-extract-candidate-commands.md).
