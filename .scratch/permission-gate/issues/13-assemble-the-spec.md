# Assemble the spec

Type: task (AFK, then a user review)
Status: resolved
Blocked by:

## Question

Every decision on the map is now made. Write `docs/permission-gate/SPEC.md`, the hand-off that someone can build the gate from, and let the user review it. This is the destination of the map.

One Markdown file that **indexes** the decisions and links each closed ticket, carrying the constants and lists a builder needs (question wording, threshold, rule lists, layout) by pointing at the ticket answer that holds them, not by restating them. Sections:

- Goal, non-goals and threat model (the gate is a tripwire; see [Charting decisions (Q1–Q18)](01-charting-decisions.md) and `docs/adr/0001-permission-gate-only-escalates.md`).
- What is judged: tools, matcher, the state sent to Jev (tool name and command or input only).
- The six signals and their wording, the 0.4 threshold, one call per command ([Signal wording, evaluation and thresholds](06-signals-evaluation-thresholds.md)).
- The local pre-check, always-escalate list and protected paths ([Seed the local pre-check](05-seed-local-pre-check.md)).
- The launcher, the fail-open promises, supported modes and versions ([Fail-open paths and the promises the spec makes](07-fail-open-promises.md), [Hook behavior facts](02-hook-behavior-facts.md), [Test the unproven modes](08-test-unproven-modes.md)).
- The audit log, trial mode, review, exit criteria and widening ([Trial mode and the audit log](12-trial-mode-and-audit-log.md)).
- The test plan: the labeled command set and how it was built ([Label the command set](04-label-command-set.md) and the evidence tickets), the readiness bar, and how the prototype's code was measured.
- **Deltas from the prototype** `typesafe_permission_gate.py`, collected from the closed tickets.
- **Limits stated plainly**: only 4 real dangerous commands so real recall is unmeasured until trial mode; the rule-of-three caveat; thresholds and wording are fitted to the same data they were measured on; the list of things still unverified.

The user reviews the finished spec and either accepts it or names what to change. The map is done when they accept it.

## Progress (not yet the answer): spec written, waiting for the user's review

`docs/permission-gate/SPEC.md` is written (12 sections: what it is; goals, non-goals and threat model; what the gate sees and decides; the six signals and threshold; the local pre-check; the launcher, failure behavior and support; trial mode, audit log and rollout; evidence and test plan; deltas from the prototype; limits and what is unverified; suggested build slices; decision index). Every link resolves and the quoted numbers were checked against the ticket answers. The exact question wording and the full rule lists stay in tickets 06 and 05 and are linked, not copied. The map is done when the user accepts the spec.


## Answer

**Review outcome**: the user read `docs/permission-gate/SPEC.md` and accepted it as written ("read it and accept everything"), in reply to the request to accept it or name changes. No change was requested. The spec's status line now says accepted.

**Delivered**: `docs/permission-gate/SPEC.md`, 12 sections, 26 links (all resolve), quoted numbers checked against the ticket answers. It indexes the twelve closed tickets, carries the deltas from the prototype, states the limits plainly, and lists what is still unverified.

**Map complete**: all thirteen tickets are resolved, no tickets are open, and no fog remains.
