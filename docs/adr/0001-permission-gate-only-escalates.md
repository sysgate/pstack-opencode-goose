---
status: accepted
---

# The permission gate can only escalate

The gate never grants permission and, in v1, never blocks outright: its only outputs are escalation or no opinion. Its judgments come from a probabilistic model, so a wrong or manipulated judgment must cost at worst one extra prompt, never a skipped one or an unrecoverable block.

**Considered options**

- *Allow calls judged low-risk*: rejected. A miscalibrated or manipulated judgment would silently bypass the user's prompt, turning a tripwire into an authority.
- *Block calls judged high-risk*: rejected for v1. A block gives the user no chance to override a false positive. Revisit once behavior in unattended runs is known.

**Consequences**

- False positives cost friction; false negatives fall back to the user's normal permissions, unchanged.
- The gate can add prompts but can never remove them.
- Where nothing can answer a prompt (headless `-p` runs), an escalation acts as a denial, so the gate does block flagged commands there. This is fail-closed and was verified in the mode tests, but it means "never blocks" holds only for interactive sessions.
