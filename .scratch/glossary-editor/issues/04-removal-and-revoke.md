# Removal and revoke: how a term leaves the glossary

Type: grilling
Status: resolved
Blocked by:

## Question

A term, avoided word or note removed from the Markdown is not detected today, and nothing is ever deleted. The charting decisions say the loader *reports* it and a human *revokes* it. Decide for the spec:

- What the loader reports (a new command, or part of `status`) and how a removal is told apart from a rename or a move to another group.
- How a human revokes: the command, what it requires (a name, a real note), and what the editor shows before it is run.
- What a revoke **cascades** to: the term's own avoid claims, claims that point at it (avoid aliases, collisions naming it), its group claim, and an outside usage only that term used.
- What the store asserts about a term once it is revoked, and what `define` and the lint hook say.

Facts from [The store's lifecycle facts](02-store-lifecycle-facts.md) that these decisions must answer:

- The store lets a `sys:` actor revoke a term, a claim or evidence, and lets a claim be revoked with an empty note. "Only a human revokes, with a note" is therefore not enforced anywhere; where does it live (the loader command, the editor, or both) and how is it made hard to bypass?
- Revoking a **term** challenges every admitted claim that uses it; revoking a **claim** cascades to nothing; revoking **evidence** voids its bindings and challenges the claim. Which of these does a removal from the Markdown call for, and in what order?
- A term cannot be revised in the store, only revoked or reopened as a new term. What does that mean for a term whose avoid words all go away?
- From [Revise mechanics](03-revise-mechanics.md): a **removed** alias inside an edited `_Avoid_:` line is a removal, not a revise; the surviving aliases are revised. The loader must tell the two apart on the same line.
- The `status` partition there reports only claims that are still in the sources; claims that are in the store but gone from the sources are reported by this ticket's mechanism.

## Answer

Settled with the user across three grilling rounds; every recommendation was accepted. Store facts are in [The store's lifecycle facts](02-store-lifecycle-facts.md); the parallel decisions for a changed term are in [Revise mechanics](03-revise-mechanics.md).

**What counts as removed.** A claim in the store (pending, admitted or challenged) that is not the current claim of any statement in the sources. An alias dropped from an `_Avoid_:` line, a changed note, a changed group and a renamed term all appear as removed old claims plus new claims; the loader never guesses that something was renamed or moved. Each removed claim is named by its source anchor, and where a new claim shares the anchor (a changed note) the report says it was replaced. A term removed while a collisions row still names it makes the loader fail loudly ([Collisions list](05-collisions-list-format.md)), so the report says its collision rows must go first.

**Load (the machine step) withholds a removed claim at once.** For a removed claim that is admitted, load **challenges** it as `sys:adjudicator` with the reason "no longer in the sources": nothing is final and the claim stops being asserted. This is the same rule as for a changed term: the machine may only make the store less assertive, immediately and reversibly. Resumable, like the revise step. A claim already challenged (a revision pending) stays challenged. A pending claim is not asserted, so load leaves it.

**A human finalizes it, with one command.** `glossary revoke --by human:NAME --note "..."`, selecting with `--term T`, `--anchor A` or `--all-removed --expect N`:
- refuses a non-human `--by`, an empty note and a placeholder note (the rules `verify` uses);
- refuses any claim still in the sources (a live claim is revised, never revoked);
- has no default selection; `--all-removed` requires `--expect N` to equal the count the report showed, so a bad edit that deleted a section cannot be revoked in one careless run;
- one transaction per claim, reported per claim, with the human as the actor. A challenged claim gets a review and then a revoke; an admitted one that load has not yet reached is revoked directly; a claim that was loaded but never verified is **denied** (review, then reject) and reported as "denied (never verified)";
- it is the only thing in the loader that ever revokes. The store enforces none of these rules (a `sys:` actor can revoke with an empty note), so the command is the only gate.

**What a revoke touches.** Claims only. Terms, aliases, notes, groups and outside usages stay admitted but unused: they assert nothing, and revoking a term object would challenge every claim that uses it, including unrelated knowledge. The claim's evidence is left admitted, as for revisions.

**Coming back.**
- **Put back before revoking:** the entry returns while the claim is still challenged; a human's verify **reaffirms** it, the same as reverting an edit.
- **Put back after revoking (or after a denial):** load proposes a **successor** pending claim reopened from the revoked or denied claim (the only legal route, because the id would otherwise be a duplicate), with a candidate; a human verifies it. This is also the undo for a mistaken revoke.

**Reporting.** `status` gets a section "removed from the sources", grouping claims by term with their states: removed and withheld (challenged), never verified (pending), revoked or denied (done, no longer listed). The status partition from [Revise mechanics](03-revise-mechanics.md) gains **restored, awaiting verification** (a revoked or denied claim whose statement is back in the sources), and "needs attention" narrows to states the loader never produces.

**In the editor.**
- A **Remove term** action deletes the entry block from the Markdown (git holds the history), previews how many claims will then be reported as removed, and **refuses while any collisions row names the term**. It never revokes.
- A removed-claims panel lists what load has withheld. Before the revoke command is built it shows, for each claim, its admitted text, who verified it and when, its state, and whether a whole term or a single alias is going away. The command builder follows the verify rules (a name with no spaces, a real note) and shows the command without running it.
- Two acts read as two acts: **remove** edits the source; **revoke** (or **deny**, for a claim never verified) is the store's human step.

**Left to other tickets.** What `define` and the lint hook say about a term whose claims are all withheld or revoked: [What readers say about a withheld term](09-what-readers-say-about-a-withheld-term.md).

**What changes in the loader** (deltas for the spec): removal detection by the id chain; load's challenge of removed claims; the `revoke` command; the status section; successor proposal from a revoked or denied claim; verify's reaffirm for a put-back entry.
