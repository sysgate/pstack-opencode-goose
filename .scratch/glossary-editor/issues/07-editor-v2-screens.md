# Editor v2 screens

Type: prototype
Status: resolved
Blocked by: 

## Question

Once the mechanics are decided, what should the new states look like? Make a cheap, rough artifact to react to (a static page or annotated sketch, not the build) for: a term being revised (old text withheld, new text pending), a term reported as removed and the revoke step, the collisions list, and the verify panel with the exact source text. Decide the layout and the wording, keeping the word **term** and the word **revoke**.

From [Removal and revoke](04-removal-and-revoke.md), the screens must also cover: the **Remove term** action (with the count of claims it will report as removed, and the refusal while a collisions row names the term), the removed-claims panel with each claim's admitted text, verifier and date, and the revoke command builder. Keep **remove** (the source) and **revoke** or **deny** (the store) visibly separate.

From [What readers say about a withheld term](09-what-readers-say-about-a-withheld-term.md): the editor's list pills use the source-versus-store names, and each claim's detail view shows the projection label and the recorded reason from the closed list, worded exactly as `define` words them. The screens must also carry the next-step line for each state (load, verify, revoke).

## Answer

Settled with the user after reacting to the [prototype](../prototype/editor-v2-screens.PROTOTYPE.html) (three structurally different variants of the same editor shell, on a made-up mid-flight glossary). The user chose **variant C, term-centred**, with the command builder **inline** (not a drawer), the Remove term consequences **inline**, and a **distinct pill for reaffirms**. The prototype is throwaway, stays uncommitted, and is the primary source for the look; it writes and runs nothing.

**Layout: the term is the unit.**
- **Header:** the v1 chips, extended with the new counts (claims, verified, to load, to verify, removed and withheld).
- **Left:** v1's term list, each term with a pill in the source-versus-store names, and **Collisions** as its own item with a pill for its state.
- **A term's page** has the v1 term form (unchanged) above a **table of its claims**. A row shows the claim (expandable), its **state** as a pill, what the **store says** (the projection label and the recorded reason from the closed list, worded exactly as `define`), and the **next step** (load, verify, revoke, or none). Expanding a claim shows the case body: a revision shows the old admitted text next to the new with the changed words marked; a reaffirm shows "unchanged since verified on `<date>` by `<who>`"; a restored claim shows when it was revoked and the note; a removed claim shows the admitted text being retired, who verified it and when; a drifted one shows the saved change against what the store still asserts. Below the table, the collisions that name this term are listed.
- **Remove term** is a button in the term's header. It opens an **inline consequences box** (no modal): the count of claims that will then be reported as removed, with Remove and Cancel; or, if a collisions row names the term, a plain-text **refusal** naming the number of rows. It never revokes.
- **Collisions** is a table of the pairs (Term, In, Must not be confused with, In, Why), one row per pair with a state pill and an Add a pair button.

**Commands are inline, in a "The database" panel under the term page** (variant A's panel, kept with C's layout). It holds three sections: **Load** (the page runs it; it admits nothing), **Verify** and **Revoke**. Verify shows a count per case, one checkbox per term (all ticked by default), and the command builder; Revoke lists the removed claims with the same builder. The builder shows the selection, the **digest** (which changes when the selection, the text or a claim's state changes), a name field and a note field with the rules from [The verify panel](06-verify-panel-source-text.md), and a Copy command button that stays disabled until the name and note are valid. The page never runs verify or revoke. There is no drawer and no tray; the per-term ticks live in this panel, and a term's page may link to its place in it.

**Words.** Pills use the source-versus-store names, and a reverted edit or a put-back entry (the reaffirm case) gets its own: **awaiting reaffirm**, because its text did not change and "revision awaiting verification" reads wrongly for it. This amends the bucket lists in [Revise mechanics](03-revise-mechanics.md) and [What readers say about a withheld term](09-what-readers-say-about-a-withheld-term.md). The words are **term**, **revise**, **revoke**, **remove** (the source) and **deny** (a claim never verified).

**What changes from editor v1** (deltas for the spec): the claims table on each term's page; the "The database" panel replacing v1's short database panel; the case-grouped verify section with diffs; the removed-claims section with the revoke builder; the Remove term action and its refusal; the collisions table screen; the new pills and next-step lines; the projection label and reason on every claim. The term form itself, the list and the search are unchanged.
