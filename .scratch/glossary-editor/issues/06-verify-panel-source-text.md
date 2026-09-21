# The verify panel: showing the exact source text

Type: grilling
Status: in progress (claimed by the wayfinder session working the map; needs the user)
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
