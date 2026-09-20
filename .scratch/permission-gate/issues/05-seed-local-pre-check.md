# Seed the local pre-check

Type: grilling (HITL)
Status: resolved
Blocked by: 03

## Question

What does the local pre-check contain at v1? Using what the candidate commands actually look like:

- Which secret-like patterns count (token formats, key files, `export KEY=...`, keychain reads) and escalate without sending anything.
- The initial always-escalate entries, each with a one-line justification (the starting point is `sudo`, `rm -rf` on `~` or `/`, force-pushes, `curl | sh`).
- The protected paths: the skip list file, the gate's own scripts and config, the audit log, `.claude/settings*`, shell profiles, scheduled-job files. Any write to these escalates.
- What the fast path covers (the current prefix list) and what it must never cover.

The answer is the concrete v1 list, each entry justified, plus the rule for how entries are added later.

## Facts found while grilling (not yet the answer)

Measured on the 158 usable real Bash commands by `tools/analyze_precheck.py` (counts and shapes only; no command text printed).

- **The current fast path covers 0 of 158.** 93% of commands contain a shell metacharacter and 15% start with `cd <dir> &&`. A segment-aware fast path (every `&&`/`;`/`|` segment in a read-only set, no substitution, redirect, heredoc, `xargs`, `eval` or `-exec`) would cover 19 (12%) with a broad set including `echo`, `cat`, `head`, `sed`; only 2 (1.3%) with a strict set. Real commands are mostly multi-line scripts, heredocs, `python3 -c` and `echo` separators. Nearly every command will therefore reach Jev.
- **Seed rule hits** (share of the 158): sudo 0, pipe-to-shell 0, force-push 0, `rm` recursive/force on home, root or cwd-wide 0. `rm` with recursive/force flags appeared 19 times but only on project-relative, regenerable or temp targets.
- **Secret behaviors**: keychain read 1, ssh key or .pem 1, `.env` mention 4, env dump 0, secret-named variable reference 0, credential files 0.
- **Protected-path writes (mention plus a write-like verb)**: gate files 7, agent settings/hooks/skills 5, shell profile 1, everything else 0. These come mostly from building the gate itself. The mention-plus-verb test is coarse: it also matches reading a file while a heredoc or redirect appears elsewhere in the same command.
- **The whole proposed seed union escalates 18 of 158 (11.4%)**, over the 5% precision bar, almost all from protected-path writes and `.env` mentions.
- **Literal-secret hits**: 7 excluded rows: 3 real-looking assignment/flag/header patterns and 4 from the generic long-token rule (2 distinct shapes: a 36-character lowercase hyphenated string at 4.03 bits per character, and a 49-character mixed-case string with underscores at 4.32; random secrets would usually score 5 or more, so these look like identifiers).
- **Scope gap**: Claude Code hook inputs give absolute, `~`-expanded paths for Write, Edit and Read, so a protected-path check on those tools cannot be dodged by `~` or a relative spelling. Bash paths are plain text and easy to obscure (variables, `cd` then relative paths, globs). Q3 excluded Write/Edit, so an agent can edit `.claude/settings.json` with the Edit tool and the gate never sees it.

## Answer

All six recommendations accepted (Q23 to Q28). This is the concrete v1 local pre-check.

**Order of checks**: local pre-check, then fast path, then Jev. The fast path can never mask a pre-check hit.

**1. Literal secrets (escalate locally, send nothing)** (Q23)
- Known token prefixes (Anthropic and OpenAI `sk-`, GitHub `gh?_` and `github_pat_`, Slack `xox?-`, AWS `AKIA…`, Google `AIza…` and `ya29.`), PEM private-key blocks, JWTs, Authorization/Bearer headers with a literal value, credentials embedded in URLs, and secret-named assignments or flags with a literal value (a `$VAR` reference is not a literal).
- The generic long-random-string rule stays a redaction backstop only. It never escalates by itself. Justification: the two remaining hits look like identifiers (entropy about 4.0 to 4.3, where random secrets usually score 5 or more), and false alarms cost prompts.
- The `ask` message names the pattern type and never repeats the matched text.

**2. Commands that read secrets (escalate locally)** (Q24)
- A keychain read that prints the value (`security find-generic-password` or `find-internet-password` with `-w`, `dump-keychain`).
- Reading private keys or `.pem` files (`~/.ssh/id_*`, `*.pem`).
- Printing the whole environment (`printenv`, bare `env`).
- Printing or copying `.env` contents (`cat`, `head`, `tail`, `less`, `source`, `cp`, `scp`, `curl -d @.env`).
- A bare mention of `.env`, credential files (`.netrc`, `.aws`, `.npmrc`, `.pypirc`, Docker config), and secret-named variable references go to Jev's `reads_secrets` signal instead. Justification: `.env` mentions alone would have escalated 4 of the 158 real commands.

**3. Destructive and irreversible entries (escalate locally)** (Q25)
- `sudo`; `rm` with recursive or force flags on home, root or a whole working directory; `git push` with force flags; pipe-to-shell (`curl … | sh`, `bash <(curl …)`, `eval "$(curl …)"`). Each matched 0 of the 158 real commands, so the cost is nil. Ordinary `git push` and `rm` on project files stay with Jev.

**4. Protected paths** (Q26)
- **Set**: `~/.claude` and project `.claude/` (settings, hooks, skills, plugins), `.claude.json`, `.mcp.json`, shell profiles, crontab and launchd files, `/etc`, ssh `config` and `authorized_keys`, and the gate's own scripts, config, skip list and audit log. `CLAUDE.md` and `AGENTS.md` are deliberately excluded because agents edit them legitimately and often.
- **Rule**: escalate a write whose target is a protected path; reading one is not escalated. This replaces the coarse mention-plus-verb test, which produced most of the 11.4% seed hit rate.
- **Scope change (amends [Charting decisions](01-charting-decisions.md))**: the hook also matches `Write`, `Edit` and `NotebookEdit`, for protected paths only, as a purely local check with no Jev call and nothing sent. Hook inputs give absolute, `~`-expanded paths for those tools.
- **Known limit**: Bash path matching is plain text and can be evaded (variables, `cd` then relative paths, globs). Jev's `tampers` signal is the second layer, and the gate remains a tripwire.
- **No off-switch** while the gate is being built; expect prompts on its own files.

**5. Fast path** (Q27)
- Keep the current small prefix list unchanged (`ls`, `pwd`, `whoami`, `date`, `wc`, `which`, and `git status`/`diff`/`log`/`show`/`branch`, with no shell metacharacters). It returns no opinion, never allow. No segment-aware parser: it would cover about 12% at best and a splitter bug would be a bypass. Plan on nearly every command being judged, with the roughly 0.3 second cost and redacted text leaving the machine.

**6. How the list grows** (Q28)
- At most 30 entries. Each carries a one-line justification, the date, and a pointer to the audit-log miss that motivated it. Only the user adds entries, the list file is a protected path, and the list is reviewed whenever trial-mode data comes in.

**Left for measurement, not decided here**: the real escalation rate of the narrowed protected-path rule. It is added to [Signal wording, evaluation and thresholds](06-signals-evaluation-thresholds.md).

## Correction (found while working [Label the command set](04-label-command-set.md))

The measurement of `rm` on the working directory missed the `./*` spelling. One real command matches (`rm -rf ./*` after `cd` into a temp folder), so the rule's real cost is 1 of 158 (0.6%), not 0. The decision itself is unchanged.


## Amendments (from [Signal wording, evaluation and thresholds](06-signals-evaluation-thresholds.md))

- **New always-escalate entries** (decision Q40): `claude plugin install`, `claude plugin marketplace add`, `claude mcp add`. Justification: two labeled real dangerous commands of this class; Jev scored the plugin install only 0.48 under wording v2. A deliberate exception to "only from logged misses". The list stands at 3 entries beyond the seed families.
- **Data heredocs are text, not commands**: the non-secret rules skip the body of `cat >> file <<EOF`; interpreter heredocs are still scanned; the literal-secret rule reads everything.
- **`cp`, `ln`, `install`** write only their last argument.
- **Measured**: 2 of 154 real routine commands escalate locally (1.3%), 2 of 4 real dangerous, 17 of 78 dangerous invented Bash.
