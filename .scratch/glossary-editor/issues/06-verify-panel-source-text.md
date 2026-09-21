# The verify panel: showing the exact source text

Type: grilling
Status: resolved
Blocked by: 

## Question

Verify stays a command the page builds, and the page must show the exact source text being attested. Decide:

- What is shown for each pending claim: the source text, and for a revision the old admitted text next to the new one.
- Whether verification can be limited to chosen claims or is always "everything pending", and what the loader's `verify` supports today.
- The rules for the name and the note (the name has no spaces; a placeholder note is refused), and whether the page should also refuse a note that does not mention what changed.
- What the page shows after the command has been run elsewhere (how it learns the claims are now verified).

Facts from [Revise mechanics](03-revise-mechanics.md) that these decisions must answer:

- `verify` now handles **three cases** per claim: a new claim, a revision (the old claim is challenged and a successor is created), and a revert (a reaffirm). The panel should say which case each pending claim is, and for a revision show the old admitted text next to the new.
- `verify` runs one transaction per claim and reports per claim; the panel should show what succeeded and what did not.
- The human named by `--by` becomes the actor on the revise, close and reaffirm receipts, so the note should say what was reviewed for the whole set.
- From [Removal and revoke](04-removal-and-revoke.md): `verify` also handles a **fourth case**, a *restored* claim (a successor reopened from a revoked or denied claim), and a put-back entry is another **reaffirm**. Load now also withholds *removed* claims, so the panel may meet challenged claims that need a reaffirm and not a revision.

## Answer

Settled with the user across two grilling rounds; every recommendation was accepted. It builds on [Revise mechanics](03-revise-mechanics.md) and [Removal and revoke](04-removal-and-revoke.md), which created the four cases the panel must show.

**What the panel shows.** Pending claims are grouped by case and by term, with a count per case at the top. For each claim:
- a **new** claim shows the source text being attested;
- a **revision** shows the old admitted text next to the new, with the changed words marked;
- a **reaffirm** (a reverted edit or a put-back entry) shows "unchanged since verified on `<date>` by `<who>`", with the text;
- a **restored** claim shows when it was revoked or denied, by whom and their note, next to the text it now has;
- a claim that is still pending after a failed boundary check shows the recorded reason ("last check failed: `<reason>`"), read from the receipt the store already keeps. The panel invents no second place for errors; the per-claim report in the terminal and a non-zero exit code are the record of a run.

**Selection is explicit and the attestation is exact.** `verify` no longer verifies "everything pending" by default. It requires a selection (`--term T`, repeatable, `--anchor A`, or `--all-pending`) plus `--confirm DIGEST`. A selection-free `verify` is refused: that is a delta from today's CLI.
- The **digest** is a hash over the sorted lines `<claim id> | <case> | <candidate id>` of the selected claims. The candidate id already hashes the source location, anchor and text, so any change to the text, the selection or the case (someone else verified a claim; an entry was put back) changes the digest, and the loader refuses with "the sources changed since the panel was rendered: refresh the page". This makes "the exact source text" enforceable, not only displayed.
- The panel has **one checkbox per term** (all its claims together), all checked by default; unchecking a term drops it. The command is built from the checked terms and is disabled when none is checked. It shows the digest beside the list and shows the command; the page never runs it.

**Revoke uses the same guard.** [Removal and revoke](04-removal-and-revoke.md) is amended: `glossary revoke` takes `--confirm DIGEST`, computed the same way over the exact claims, their state and the candidate id of the admitted evidence being retired, and this **replaces** `--expect N`. One guard on both commands: "this is exactly what I saw".

**Name, note and one note per run.** The name has no spaces and a placeholder note (`...`, `todo`, too short) is refused by the loader's CLI as well as by the page; today the loader only checks that the note is non-blank. There is no rule that the note must mention what changed: the receipts already name every claim. The command takes **one note** for everything selected, recorded on every receipt of that run; different reviews are separate runs.

**How the page learns you ran the command.** It refreshes when Refresh is pressed and when the browser window regains focus, and shows each claim's "verified by `<name>` on `<time>`" from its receipts. No polling and no push.

**What changes in the loader** (deltas for the spec): `verify` handles four cases (new, revision, reaffirm, restored) with explicit selection and `--confirm`; the digest is computed and checked; name and note rules move in; the exit code is non-zero when any claim is refused; the report lists a claim only after its transaction commits; `revoke` takes `--confirm` in place of `--expect`. The panel's layout is for [Editor v2 screens](07-editor-v2-screens.md).
