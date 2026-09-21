# Removal and revoke: how a term leaves the glossary

Type: grilling
Status: open
Blocked by: [The store's lifecycle facts](02-store-lifecycle-facts.md)

## Question

A term, avoided word or note removed from the Markdown is not detected today, and nothing is ever deleted. The charting decisions say the loader *reports* it and a human *revokes* it. Decide for the spec:

- What the loader reports (a new command, or part of `status`) and how a removal is told apart from a rename or a move to another group.
- How a human revokes: the command, what it requires (a name, a real note), and what the editor shows before it is run.
- What a revoke **cascades** to: the term's own avoid claims, claims that point at it (avoid aliases, collisions naming it), its group claim, and an outside usage only that term used.
- What the store asserts about a term once it is revoked, and what `define` and the lint hook say.
