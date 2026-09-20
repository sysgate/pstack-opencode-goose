# Permission Gate

A checkpoint that reviews an AI coding agent's tool calls before they run and can only add scrutiny, never grant permission. It exists to catch agent mistakes and instructions injected into the agent's inputs.

## Language

**Permission gate**:
The checkpoint that reviews a tool call before it runs. A tripwire on agent behavior, not a defense against a determined attacker.
_Avoid_: firewall, sandbox, security boundary, admission gate (that term belongs to CCGF)

**Signal**:
One yes/no judgment, expressed as a probability, about a tool call, such as whether it is destructive.
_Avoid_: score, flag, feature

**Threshold**:
The probability at which a signal makes the gate escalate a call. One value applies to every signal in v1.
_Avoid_: cutoff, limit

**Fail open**:
What Claude Code does when a hook cannot decide (timeout, hooks disabled, missing entry): the call proceeds under the user's normal permissions.
_Avoid_: fail safe, default allow

**Escalation**:
The gate's act of putting a human decision in front of a tool call instead of leaving it to normal permissions.
_Avoid_: alert, warning

**No opinion**:
The gate's outcome when nothing looks risky: the call proceeds through the normal permission system exactly as if the gate did not exist.
_Avoid_: allow, approve, pass

**Heartbeat**:
The entry written when a session starts to show the gate was running; a session without one means the gate was silently off.
_Avoid_: ping, check-in

**Enforcement**:
The mode in which the gate's escalations actually prompt the user, entered from trial mode once the exit criteria are met.
_Avoid_: live mode, production mode

**Fast path**:
The class of tool calls the gate does not judge at all because they are provably local and read-only.
_Avoid_: whitelist, allowlist

**Skip list**:
The short list, owned by the user, of MCP tools the gate does not judge. Empty until trial mode shows repeated harmless escalations.
_Avoid_: allowlist, whitelist

**Protected path**:
A file or folder whose modification always escalates: agent configuration, shell profiles, scheduled jobs, and the gate's own files. Reading one does not escalate.
_Avoid_: sensitive path, restricted path

**Local pre-check**:
A code-only inspection run before any judgment is requested, which escalates immediately on a match and sends nothing off the machine.
_Avoid_: pre-filter, sanitizer

**Always-escalate list**:
The short, individually justified set of known-risky patterns the local pre-check matches. An entry is added only after the audit log shows a real miss.
_Avoid_: denylist, blocklist

**Trial mode**:
The period in which the gate records what it would have done but never escalates anything.
_Avoid_: dry run, shadow mode, audit mode

**Audit log**:
The tamper-evident, append-only local record of every call the gate sees: its signals, its verdict, and a masked excerpt of the command, never the full text.
_Avoid_: history, telemetry

**Redaction**:
Removing secret-like strings from a command before it is stored or sent.
_Avoid_: scrubbing, sanitizing

**Masking**:
Replacing file names in a command with placeholders, keeping the folders, so private document names never leave the machine.
_Avoid_: anonymizing

**Labeled command set**:
The commands, each marked dangerous or routine, used as the evidence that the gate is ready: real ones from past sessions plus tagged synthetic ones.
_Avoid_: test set, benchmark, golden set

**Synthetic command**:
A hand-written command tagged as invented, used only to measure recall and never precision.
_Avoid_: fake command, mock command

**Scope**:
A named folder tree in which the gate is active. A session outside every scope is not expected to have any gate records. Widened one step at a time.
_Avoid_: workspace, coverage

**Covered tool**:
A kind of tool call the gate reviews: shell commands, MCP tool calls, and file edits (file edits only get the protected-path check).
_Avoid_: scope (that names a folder tree)

**Decider**:
The stage that produced a call's verdict: local pre-check, fast path, skip list, judgment, or fallback (the gate could not run and asked instead).
_Avoid_: source, handler

**Verdict**:
The recorded outcome for one call: no opinion, would-ask, or asked.
_Avoid_: decision, result

**Would-ask**:
The verdict recorded in trial mode for a call that enforcement would have escalated. The user was never prompted.
_Avoid_: soft escalation, shadow escalation

**Judged call**:
A call whose verdict came from a judgment, not from the local pre-check, fast path or skip list. Readiness evidence counts these.
_Avoid_: scored call, evaluated call

**Near-threshold call**:
A call whose highest signal is at least 0.25 but under the threshold. Reviewed because it is the likeliest place for a miss.
_Avoid_: borderline call (that describes a hand-written synthetic case)

**Mark**:
The user's label of a reviewed call as dangerous or routine. The latest mark on a call wins.
_Avoid_: tag, annotation

**Reconciliation**:
Comparing the tool calls a session's transcript shows with the calls the audit log recorded, to expose silent gaps where the gate did not run.
_Avoid_: audit (that names the log itself), sync
