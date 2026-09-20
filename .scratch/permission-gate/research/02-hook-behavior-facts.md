# Hook behavior facts: PreToolUse "ask" vs allow rules, modes, headless, subagents, timeout

Answers issue `.scratch/permission-gate/issues/02-hook-behavior-facts.md`.

- Researched: 2026-09-19, from the live Anthropic docs (fetched as `.md`). The pre-existing scratchpad copy of `hooks.md` was byte-identical to the live fetch.
- Sources (all first-party, code.claude.com):
  - hooks: https://code.claude.com/docs/en/hooks.md
  - hooks-guide: https://code.claude.com/docs/en/hooks-guide.md
  - permissions: https://code.claude.com/docs/en/permissions.md
  - permission-modes: https://code.claude.com/docs/en/permission-modes.md
  - headless: https://code.claude.com/docs/en/headless.md
  - sub-agents: https://code.claude.com/docs/en/sub-agents.md
- Marking: DOCUMENTED = a verbatim quote states it. INFERRED = follows from quoted text but no sentence says it. NOT STATED = docs silent.
- The docs are version-gated in places (for example v2.1.211 for auto-mode `ask`). The installed Claude Code version was not checked (no `claude` runs allowed).

## Summary

| # | Question | Answer | Status | Confidence |
|---|----------|--------|--------|------------|
| 1 | Hook `"ask"` when an allow rule already matches | Hooks run before the permission prompt; `"ask"` "prompts the user to confirm" with no carve-out for allow rules, and permissions.md says a hook can "force a prompt". No sentence says "hook ask beats allow rule" verbatim. | DOCUMENTED (strong implication, not verbatim) | Medium-high |
| 2a | `ask` in `default` | Shows the normal permission prompt | DOCUMENTED | High |
| 2b | `ask` in `plan` | Hook fires (all modes). Effect of `ask` in plan not stated | NOT STATED | Low |
| 2c | `ask` in `acceptEdits` | Hook fires (all modes). Effect of `ask` not stated | NOT STATED | Low |
| 2d | `ask` in `auto` | Forces a prompt; classifier may still deny but cannot approve silently (v2.1.211+) | DOCUMENTED | High |
| 2e | `ask` in `dontAsk` | Hook fires. `dontAsk` "auto-denies every tool call that would otherwise prompt", so `ask` very likely becomes deny. Not stated for hook `ask` | DOCUMENTED (fires) / INFERRED (deny) | Medium |
| 2f | `ask` in `bypassPermissions` | Hook `deny` is honored there. Hook `ask` not stated; "actions no mode auto-approves" list does NOT include hook `ask` | NOT STATED | Low |
| 3 | `ask` in headless `-p` | Generic rule: with no permission host, anything that would prompt is denied. Not stated for hook `ask` specifically | INFERRED | Medium |
| 4 | Subagent tool calls fire PreToolUse; input identifies them | Yes; `agent_id` and `agent_type` in input | DOCUMENTED | High |
| 5 | Slow hook vs `timeout` | Hook cancelled, output discarded, call is NOT blocked: continues through the normal permission flow (fail-open). Default command timeout 600 s | DOCUMENTED | High |

## 1. Hook `"ask"` when a settings `permissions.allow` rule already matches

Documented facts:

- Hooks run before the permission prompt, and can force one.
  - permissions.md, "Extend permissions with hooks": "PreToolUse hooks run before the permission prompt, for every tool except `EndConversation`. The hook output can deny the tool call, force a prompt, or skip the prompt to let the call proceed." https://code.claude.com/docs/en/permissions.md
- The decision field definition.
  - hooks.md, PreToolUse decision control: "`\"ask\"` prompts the user to confirm." Contrast with `"allow"`, which is listed with exceptions ("except for the actions no mode auto-approves..."). `"ask"` has no stated exception. https://code.claude.com/docs/en/hooks.md
  - hooks-guide.md: "`\"ask\"`: show the permission prompt to the user as normal". https://code.claude.com/docs/en/hooks-guide.md
- Hook decisions vs rules (deny/ask only are discussed):
  - permissions.md: "Hook decisions don't bypass permission rules. Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns: a matching deny rule blocks the call, and a matching ask rule still prompts even when the hook returned `\"allow\"` or `\"ask\"`."
- Rule order (rules only, hooks not part of it):
  - permissions.md: "Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome".
- Precedence among several hooks:
  - hooks.md: "When multiple PreToolUse hooks return different decisions, precedence is `deny` > `defer` > `ask` > `allow`." All matching hooks run in parallel ("All matching hooks run in parallel.").
- A blocking hook beats allow rules: "A hook that exits with code 2 stops the tool call before permission rules are evaluated, so the block applies even when an allow rule would otherwise let the call proceed." (permissions.md)

What is NOT stated: no sentence says "a hook `ask` overrides a matching `permissions.allow` rule". The evidence is (a) hooks run before the prompt and are described as able to "force a prompt", (b) `"ask"` is defined without an allow-rule exception, (c) the auto-mode note (section 2d) that a hook `ask` forces a prompt even where the classifier would otherwise approve. Treat as very likely, but confirm with the test below before relying on it for the ~37 allow rules.

## 2. Behavior of `"ask"` per permission mode

Common fact (hooks-guide.md, "Hooks and permission modes"): "`PreToolUse` hooks fire before any permission-mode check, in every permission mode, including `dontAsk`." So the hook runs in all six modes; the question is only what `ask` then does. The hook input carries `permission_mode` (`"default"`, `"plan"`, `"acceptEdits"`, `"auto"`, `"dontAsk"`, `"bypassPermissions"`; Manual arrives as `"default"`), so the gate can log the mode.

- **default (Manual)**: DOCUMENTED. "`\"ask\"`: show the permission prompt to the user as normal" (hooks-guide.md). The prompt is labelled with its source: "`[settings]` for a hook from any settings file" (hooks.md).
- **plan**: NOT STATED for hook `ask`. Related: permission-modes.md says plan mode's blocks apply except in interactive terminals with bypass permissions available, where "a file edit or shell command it attempts during planning runs without prompting" while "Explicit ask rules ... still prompt". That sentence names ask rules, not hook `ask`.
- **acceptEdits**: NOT STATED for hook `ask`. The mode only auto-accepts edits and common filesystem commands; the docs do not say a hook `ask` on those is still prompted. (headless.md: "The actions no mode auto-approves still apply" - a list that does not name hook `ask`.)
- **auto**: DOCUMENTED. hooks.md: "A hook's `\"ask\"` also forces a permission prompt in auto mode: the classifier can still deny the tool call, but it can't approve the call silently. Before v2.1.211, the classifier could approve a Bash command running outside the sandbox without showing the prompt the hook requested; the classifier still applied its own safety rules to that command, and a hook `\"deny\"` was always honored." permission-modes.md adds: the "switch to auto" option is not offered on prompts "forced by ... a hook, because auto mode still shows you those prompts". Version caveat: below v2.1.211, Bash outside the sandbox could bypass the requested prompt.
- **dontAsk**: hook fires (documented above). Outcome of `ask`: INFERRED deny. permission-modes.md: "If you set `dontAsk` mode, Claude Code auto-denies every tool call that would otherwise prompt you ... plus actions matching your `permissions.allow` rules and calls approved by a PreToolUse hook." Also "Claude Code denies calls matching your explicit `ask` rules rather than prompting." Nothing says hook `ask` specifically; the generic sentence covers it if a hook `ask` counts as "would otherwise prompt". Mark unverified.
- **bypassPermissions**: NOT STATED for hook `ask`. Documented adjacent facts: hook `deny` still blocks ("A hook that returns `permissionDecision: \"deny\"` blocks the tool even in `bypassPermissions` mode", hooks-guide.md). "Deny rules block in every mode, including `bypassPermissions`. ... Allow rules have no effect in `bypassPermissions`." The list "Actions no mode auto-approves" (permission-modes.md) names ask rules, org-`ask` connector tools, user-interaction tools, critical-path `rm`, cross-session safeguards, outside-directory reads - hook `ask` is absent, so a hook `ask` may not prompt in this mode. Do not assume the gate works in bypass; use hook `deny` semantics there if bypass matters.

## 3. `"ask"` in headless `claude -p`

- NOT STATED for hook `ask` specifically.
- Generic documented behavior, headless.md "Turn off permission prompts in unattended runs": "Anything that would prompt is denied unless a `PermissionRequest` hook allows it, Claude is told that nobody can approve the request and not to retry it, and the run continues. In a `-p` run with no host, these requests are denied either way". A "host" is an Agent SDK `canUseTool` callback or `--permission-prompt-tool` MCP tool; with one present and without `--permission-prompts none`, "your run waits for that host to answer each permission request."
- hooks.md, PermissionRequest: "In sessions that can't show a prompt, such as background subagents in non-interactive mode, Claude Code still runs these hooks, and if no hook returns a decision, it denies the tool call."
- hooks.md (PreModelSwitch only): "Only `/model` in an interactive session can show the `\"ask\"` prompt. On every other surface, including non-interactive mode with the `-p` flag ... Claude Code treats `\"ask\"` as a refusal." This is for PreModelSwitch, NOT PreToolUse; do not transfer it, but it shows the analogous design.
- `-p` starts in Manual mode on every plan (headless.md), and `-p` runs project hooks without a trust dialog (headless.md), so a settings-file gate does run in `-p` (unless `--bare` or `disableAllHooks`).
- Best reading: hook `ask` in `-p` without a host becomes a denial (fail-closed) - INFERRED, medium confidence.

## 4. Subagents

DOCUMENTED, yes, and identifiable.

- hooks.md, "Hook locations": "Hooks from settings files, managed policy settings, and plugins also run inside subagents. When a subagent calls a tool, tool events such as `PreToolUse` and `PostToolUse` fire the same configured hooks as in the main conversation, and the input carries the `agent_id` and `agent_type` common input fields that identify the subagent."
- hooks.md, common input fields: "`agent_id`: Unique identifier for the subagent. Present only when the hook fires inside a subagent call. Use this to distinguish subagent hook calls from main-thread calls." and "`agent_type`: Agent name (for example, "Explore" or "security-reviewer"). Present when the session uses `--agent` or the hook fires inside a subagent."
- sub-agents.md, "Define hooks for subagents": "Hooks from settings files, managed policy settings, and plugins all apply inside subagents, so a `PreToolUse` hook in `settings.json` also runs before every tool a subagent uses."
- Note: `agent_type` also appears for a main session started with `--agent`; only `agent_id` marks a real subagent call.
- Prompts from subagents: sub-agents.md: "When a background subagent reaches a tool call that needs permission, Claude Code surfaces the prompt in your main session and names the subagent that is asking." (Before v2.1.186 background subagents auto-denied such calls.) Subagent permission mode: "When the main conversation is in `bypassPermissions`, `acceptEdits`, or auto mode, the subagent runs in that same mode"; in `default`/`dontAsk`/`plan` it can use its own `permissionMode` (except `bypassPermissions`).
- The Agent tool itself is also a PreToolUse tool (hooks.md lists `Agent` among matchable tools), but the gate's matcher `Bash|mcp__.*` will not match it. Subagent Bash and MCP calls do match.

## 5. `timeout` and a slow hook

DOCUMENTED. A timed-out command hook fails open.

- hooks.md, "Timeouts": "Claude Code cancels a `command`, `http`, or `mcp_tool` hook that reaches its `timeout`, discarding the hook's output, so on most events a timed-out hook renders no decision. ... On `PreToolUse` ... A timed-out `command`, `http`, or `mcp_tool` hook doesn't block the tool call. The call continues through the normal permission flow, so don't count on a stalled hook to act as a gate." (Contrast: an Agent SDK callback hook that exceeds its timeout "blocks the tool call".)
- Result for the gate: a slow hook yields neither ask nor deny; the call proceeds under normal rules, meaning a matching `permissions.allow` rule then lets it run with no prompt.
- Unit and default, hooks.md common fields: "`timeout`: Seconds before canceling. ... Defaults: 600 for `command`, `http`, and `mcp_tool`; 30 for `prompt`; 60 for `agent`." (Lower defaults apply only to UserPromptSubmit, PreModelSwitch, PostModelSwitch, MessageDisplay, SessionEnd; not PreToolUse.) So the default for a PreToolUse command hook is 600 s; a 3 s ceiling must be set explicitly (`"timeout": 3`).
- Other fail-open paths (hooks.md, "Exit code output"):
  - "For most hook events, exit code 2 is the only exit code that blocks through the code alone. Without valid JSON on stdout, Claude Code treats exit code 1 as a non-blocking error and proceeds with the action".
  - A missing or non-executable script "lands in the same non-blocking bucket ... a mistyped path in `settings.json` leaves the gate silently disabled."
  - Invalid or schema-failing JSON on exit 0 is a "non-blocking error: the action proceeds."
  - Exit 2 blocks (deny), "even a JSON `permissionDecision` of `\"allow\"` can't override it" - so an `ask` gate should never use exit 2 for its "no opinion" path, and should exit 0 with empty stdout for no opinion ("exit 0 ... No decision: the normal permission flow applies").
  - Misplaced field: "`permissionDecision` belongs inside `hookSpecificOutput`, not at the top level"; a top-level one is silently ignored (hooks-guide.md).
  - Valid ask output shape: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "..."}}` (per the decision-control table; `permissionDecisionReason` for `ask` is shown to the user, not Claude).

## Implications for the gate

- The gate is fail-open by construction: timeout, crash, exit 1, bad JSON, or a mistyped script path all fall through to the normal flow, where the user's allow rules (and auto mode) apply. Its guarantee is "ask when it decides to", never "block when broken". Set an explicit short `timeout` (for example 3) because the 600 s default would stall the session, and consider a startup self-check for the script path.
- Emitting `"ask"` is safe against other hooks: `ask` outranks `allow` from any other hook in the same parallel batch; only `deny`/`defer` outrank it.
- Never exit 2 or emit `deny` unintentionally; that is a hard block that no allow rule or mode overrides.
- Auto mode is covered (v2.1.211+): the hook's `ask` forces the prompt and the classifier cannot silently approve. Below that version, Bash outside the sandbox could skip the prompt, so record the version.
- Subagent Bash/MCP calls hit the gate too, so the gate should tolerate `agent_id`/`agent_type` in its input and can log them; in background subagents the prompt surfaces in the main session.
- Explicit `ask` rules and deny rules are already out of the gate's hands (rules evaluate regardless of hook output); the gate only adds asks on top of allow rules and auto-mode approvals. Behavior in `plan`, `acceptEdits`, `dontAsk`, `bypassPermissions`, and `-p` is unproven; do not claim the gate protects those until tested.

## Open, needs an empirical test

Run every test in a throwaway directory with its own project-scoped `.claude/settings.json` (hook plus one allow rule), and a stub hook that writes a log line and always returns `ask` for a harmless marker command such as `echo gate-test`. Never touch `~/Projects/.claude/settings.local.json` or user settings, and use a scratch allow rule like `Bash(echo gate-test)`.

1. Hook `ask` vs matching allow rule (Q1). Interactive default mode; allow rule `Bash(echo gate-test)`; hook returns `ask`. Ask Claude to run `echo gate-test`. Expect a prompt labelled `[settings]`. No prompt means the assumption in Q1 is wrong.
2. `plan`, `acceptEdits`, `bypassPermissions` (Q2b, 2c, 2f). Repeat test 1 after Shift+Tab / `--permission-mode <mode>` for each. Record prompt or no prompt. For `bypassPermissions` only launch it in an isolated scratch directory and with the harmless command.
3. `dontAsk` (Q2e). `claude --permission-mode dontAsk` in the scratch dir; expect denial without prompt; check the denial message.
4. Headless (Q3). `claude -p "run: echo gate-test" --permission-mode default --output-format stream-json` in the scratch dir; inspect `permission_denials` in the final result to see whether the hook `ask` produces a denial or lets it run. (This needs a `claude` run, so it is left to the human.)
5. Timeout (Q5 confirmation). Hook that `sleep 5` then returns `ask`, with `"timeout": 2`; with the allow rule present, confirm the command runs unprompted and the transcript shows a timeout notice.
6. Subagent (Q4 confirmation). Have the hook dump its stdin JSON to a log; run a subagent that calls `echo gate-test`; confirm `agent_id`/`agent_type` present, and that an `ask` from a background subagent surfaces in the main session.
7. Version check: run `claude --version` and confirm it is at least v2.1.211 (auto-mode `ask` fix) and v2.1.186 (background subagent prompts).
