# What readers say about a withheld term

Type: grilling
Status: resolved
Blocked by:

## Question

While a term's revision awaits verification (its old claim is challenged), and after a term or claim is revoked, `define` and the lint hook go quiet about it, because only admitted claims are asserted. That is the safe direction, but silence is ambiguous: the user cannot tell "the glossary has nothing to say" from "the glossary is withholding something". Decide:

- Should `define` say that a term has claims withheld (it already counts them as "withheld") and why: awaiting verification, revoked, or failing the integrity check?
- Should the lint hook say anything when it stays quiet about a withheld term, or only ever advise, never explain?
- Should the editor's list mirror the same wording, so a person sees the same state in every place?
- What is the exact wording, using the words **term**, **revise** and **revoke**?

Facts from [Revise mechanics](03-revise-mechanics.md) and [Removal and revoke](04-removal-and-revoke.md): the states in which a term's claims are withheld and `define` and the lint hook fall silent are now several: a **revision awaiting verification**, **removed and withheld** (awaiting revoke), **revoked or denied**, and **restored, awaiting verification**. Decide whether the wording distinguishes them or says only "withheld", and which of them the person can act on.

## Answer

Settled with the user across two grilling rounds; every recommendation was accepted. It builds on [Revise mechanics](03-revise-mechanics.md) and [Removal and revoke](04-removal-and-revoke.md), which created the withheld states.

**Two layers, one vocabulary each.** The glossary already defines **Projection label** (how knowledge is worded when shown, derived from stored state, never authority); the code maps states to Admitted, Pending Evidence, Challenged, Revised, Revoked, Closed and Not Projectable. `define` and other readers of the store use those labels **verbatim** plus a short recorded reason. `status` and the editor, which compare the source with the store, keep their own names (not loaded, drift, loaded and unverified, revision awaiting verification, removed and withheld, restored and awaiting verification, awaiting reaffirm, needs attention) and show the matching projection label beside each. A revision awaiting verification and a removed claim are both "Challenged" in the store; the reason tells them apart.

**`define` prints one line per withheld claim** as `<what>: <projection label> (<recorded reason>)`, replacing the bare "N claim(s) withheld: not assertable". The reason comes from the receipt that made it so, never guessed. The catch-all "(not verified yet)" is retired.
- It lists only the **current claim** of each statement (the end of its chain), with a single "earlier versions: N" hint when there are any; the full lineage stays in the receipts. This also fixes the quirk where a term with an admitted successor still reported one withheld claim, because its closed predecessor counted.
- A revoked or denied claim with no successor is the current claim, so it is still listed: it is the record.
- An **integrity failure** is reported on the first line, as a fault to fix (the failing check's code and the command to run), clearly different from a per-claim state.
- `define` describes and never instructs.

**The reason clauses are a closed list.** The machine reasons are fixed strings written once, in the spec, and are the only strings the loader records; human notes are quoted verbatim. A new reason has to be added on purpose.

| Situation | Label | Reason clause |
|---|---|---|
| New claim, loaded | Pending Evidence | loaded, not yet verified |
| Successor of a revoked or denied claim | Pending Evidence | restored, not yet verified (was revoked or denied on `<date>`) |
| Source text changed | Challenged | source text changed; revision awaiting verification |
| Removed from the sources | Challenged | no longer in the sources; awaiting revoke |
| Its evidence was revoked | Challenged | its evidence was revoked |
| A term it uses was revoked | Challenged | a term it uses was revoked |
| Revoked by a human | Revoked | revoked by `<name>` on `<date>`: `<their note, verbatim>` |
| Denied by a human, never verified | Not Projectable | denied by `<name>` on `<date>`, never verified: `<their note, verbatim>` |

The words are **term** for a term, **revise** for the store's act, and **revoke** for the human's.

**The lint hook stays silent about withheld claims.** It only ever advises on what the store asserts; explaining absences would nag about things just removed on purpose. It keeps saying it is inactive when the store fails its integrity check.

**Who says what to do next.** `status` and the editor, which sit beside the commands, name the next step for each state: load a change, verify a pending claim, revoke a removed claim. Readers do not.

**The editor's list** uses the source-versus-store names as pills, and its detail view shows the projection label and recorded reason with the same strings as `define`, so the terminal and the page use the same words.

**What changes** (deltas for the spec): `define` prints per-claim lines for the current claim of each statement, with the integrity fault first; the loader records only the closed list of machine reasons on its challenge, denial and successor receipts; `status` and the editor gain the next-step lines. Whether the hypergraph web view shows these states stays in the fog.
