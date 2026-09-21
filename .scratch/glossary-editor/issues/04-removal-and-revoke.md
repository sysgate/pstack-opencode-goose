# Removal and revoke: how a term leaves the glossary

Type: grilling
Status: open
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
