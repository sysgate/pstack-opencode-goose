# Hook behavior facts: ask vs allow rules, modes, headless, subagents

Type: research
Status: resolved
Blocked by:

## Question

What does Claude Code actually do with a PreToolUse hook's `"ask"` decision in each situation the gate will meet? Establish from primary sources, marking anything the docs do not state:

1. Does a hook `"ask"` still prompt when a settings allow rule already matches the call?
2. Behavior of `"ask"` in each permission mode: default, plan, acceptEdits, auto, dontAsk, bypassPermissions.
3. Behavior of `"ask"` in headless `-p` runs with no way to prompt.
4. Whether PreToolUse hooks fire for tool calls made by subagents, and what the hook input carries for them.
5. How the hook's `timeout` setting interacts with a slow hook (a hook that exceeds its timeout), given the gate's 3 second ceiling.

Where the docs are silent, record that plainly and propose the smallest safe empirical test. Do not run one against real settings.

## Answer

Full findings with quotes and URLs: `research/02-hook-behavior-facts.md` (produced by a read-only subagent; the timeout, missing-script and default-timeout claims were re-checked against the docs by the map driver). Installed Claude Code is 2.1.278.

**Documented**
- PreToolUse hooks fire in every permission mode and inside subagents; subagent calls carry `agent_id` (only `agent_id` marks a real subagent) and `agent_type`.
- Hook `ask` shows the normal prompt in default mode, and forces a prompt in auto mode (classifier can deny but cannot approve silently; fixed in v2.1.211, so 2.1.278 is covered).
- **The gate fails open.** A hook that times out, crashes, exits 1, prints invalid JSON, or points at a missing or non-executable script does not block; the call continues through normal permissions, so a matching allow rule runs it unprompted. Only exit 2 blocks. The default command-hook timeout is 600 seconds, so a short `timeout` must be set explicitly, and "no opinion" must be exit 0 with empty output.
- `ask` outranks `allow` from other hooks; only `deny` and `defer` outrank it.

**Not stated, unproven**
- Whether a hook `ask` overrides a matching `permissions.allow` rule (strongly implied, not stated).
- What `ask` does in plan, acceptEdits, dontAsk (deny likely) and bypassPermissions (may do nothing), and in headless `-p` (deny likely).

**Consequences for the map**
- New ticket 07 settles the promise the spec makes about fail-open paths and which modes are supported.
- New ticket 08 runs the empirical tests for the unproven behaviors.
- Prototype delta: `typesafe_permission_gate.py` imports `typesafe_sdk` at the top, outside any error handling, so an import failure would exit 1 and fail open.
