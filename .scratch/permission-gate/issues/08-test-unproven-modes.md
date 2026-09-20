# Test the unproven modes

Type: task (HITL)
Status: resolved
Blocked by:

## Question

Run the empirical tests listed in `research/02-hook-behavior-facts.md` ("Open, needs an empirical test") to settle what a hook `ask` does where the docs are silent:

1. Hook `ask` versus a matching allow rule.
2. plan, acceptEdits and bypassPermissions modes.
3. dontAsk mode.
4. Headless `claude -p` with no way to prompt.
5. Timeout behavior with an allow rule present.
6. A subagent's call surfacing `agent_id` and `agent_type`, and an `ask` from a background subagent.

Every test runs in a throwaway directory with its own project-scoped settings and a stub hook that only logs and returns `ask` for a harmless marker command. It never touches user settings, `~/Projects/.claude/settings.local.json`, or any real tool call. These tests start Claude Code sessions and use model tokens, so the user must approve running them.

The answer records each test's observed result next to what the docs implied.


## Answer

**What was done** (with the user's approval, "Run the headless tests now"): 25 headless `claude -p` runs on Claude Code 2.1.278 (Haiku 4.5, about $0.22 in total) in three throwaway folders, each with a project-scoped stub hook that only logs and returns `ask` for the marker command `gate-test`. Only harmless `echo` and `mkdir` commands ran, in scratch folders, with `--setting-sources project`, no MCP servers, no skills, and a per-run budget cap. The harness is saved in `mode-tests/` (`hook.py`, `run.py`, `setup.py`, `allow.json`, `README.md`). Raw per-run JSON stayed in the scratch area.

**Results**

| Question | Result |
|---|---|
| Does a hook `ask` override a matching allow rule? | **Yes.** With the allow rule supplied via `--settings`, a silent hook let `mkdir` run (control); the same rule plus a hook `ask` was denied in 2 of 2 runs. |
| Default mode, no way to prompt | `ask` became a **denial**, not a silent allow. |
| `dontAsk` | `ask` denied; control ran. |
| `acceptEdits` | `ask` denied a command that mode would otherwise accept (`mkdir`); control ran. |
| `bypassPermissions` | `ask` was **still honored** (denied); control ran. The gate is not inert in bypass mode, at least headless. |
| `plan` | Control ran and the hook fired. `ask` was denied in the one run where the model attempted the tool; in the other 3 runs the model declined to call Bash, so no hook fired. |
| `auto` | **Not testable headless**: the hook saw `permission_mode: "default"` when `auto` was requested. The documented behavior (a hook `ask` forces a prompt) stays unverified here. |
| Subagents | The hook fired inside a subagent and received `agent_id` and `agent_type: "general-purpose"`. |
| Slow hook | A hook sleeping 6 seconds with `timeout: 2`: the command **ran unprompted**. The `ask` was discarded, so the gate **fails open on timeout**, confirming the documentation. |
| Hook input | `permission_mode` arrived as `default`, `dontAsk`, `plan`, `acceptEdits`, `bypassPermissions`. |

**A mistake caught along the way**: the first allow-rule test was invalid. A project's `permissions.allow` rules are ignored until the workspace is trusted, and `-p` cannot accept the trust dialog, so the control failed (a silent hook still got `mkdir` denied). That result was withdrawn and the test redone through `--settings`, where the control passed.

**Consequences for the spec and the fail-open ticket**
- In runs where nothing can answer a prompt (headless `-p`), an escalation acts as a **denial**: the agent is told nobody can approve. That is fail-closed, but it means the gate blocks flagged commands in unattended runs, which the ADR must acknowledge.
- The gate escalates even commands the user's allow rules pre-approve, as intended.
- Still **unverified** and left to an optional interactive checklist (in `mode-tests/README.md`): the prompt itself in interactive default, acceptEdits, bypass and auto modes.

**Side effects checked**: the user's `~/.claude/settings.json` was not modified (last change 06:47, before the first run at 07:58). `~/.claude.json`, Claude Code's own state file, changes on every run and holds no entry for the scratch folders. Three tiny transcript folders were created under `~/.claude/projects` despite `--no-session-persistence` (two empty `memory` folders and one 4 KB session folder); they held only test litter and were removed.
