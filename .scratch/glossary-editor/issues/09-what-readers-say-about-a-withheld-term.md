# What readers say about a withheld term

Type: grilling
Status: open
Blocked by:

## Question

While a term's revision awaits verification (its old claim is challenged), and after a term or claim is revoked, `define` and the lint hook go quiet about it, because only admitted claims are asserted. That is the safe direction, but silence is ambiguous: the user cannot tell "the glossary has nothing to say" from "the glossary is withholding something". Decide:

- Should `define` say that a term has claims withheld (it already counts them as "withheld") and why: awaiting verification, revoked, or failing the integrity check?
- Should the lint hook say anything when it stays quiet about a withheld term, or only ever advise, never explain?
- Should the editor's list mirror the same wording, so a person sees the same state in every place?
- What is the exact wording, using the words **term**, **revise** and **revoke**?

Facts from [Revise mechanics](03-revise-mechanics.md) and [Removal and revoke](04-removal-and-revoke.md): the states in which a term's claims are withheld and `define` and the lint hook fall silent are now several: a **revision awaiting verification**, **removed and withheld** (awaiting revoke), **revoked or denied**, and **restored, awaiting verification**. Decide whether the wording distinguishes them or says only "withheld", and which of them the person can act on.
