# Revise mechanics: what happens when a term changes

Type: grilling
Status: open
Blocked by: [The store's lifecycle facts](02-store-lifecycle-facts.md)

## Question

The charting decisions say a changed term follows the doctrine's revision path and the old claim stops being asserted at once. Given what the store actually allows, decide the exact mechanics for the spec:

- What counts as a **change**, element by element: the definition text, an avoided word added or removed, an avoid note changed, the group changed.
- The sequence of states and receipts for the old claim (challenged on load, then revised or revoked when the new one is verified) and for the new claim (proposed with the old one as predecessor), and who acts at each step.
- Whether a revise is **one atomic unit** or a **safely resumable** sequence, given that the candidate-evidence insert uses a separate connection.
- What the loader reports and what `status` shows during the window.
- What happens when the same term is edited again before the first revision is verified.
