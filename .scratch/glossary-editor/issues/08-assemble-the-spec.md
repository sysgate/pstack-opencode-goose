# Assemble the spec

Type: task (AFK, then a user review)
Status: open
Blocked by: 

## Question

When every decision on the map is made, write `docs/glossary-editor/SPEC.md`, the hand-off someone can build v2 from, and let the user review it. This is the destination of the map. It indexes every decision, lists the deltas from editor v1, states what is out of scope, and notes the cross-repo dependency (`CHI_GATEWAY_DIR` and the loader's CLI) and the two performance notes. Alongside it, **draft** (do not apply) the doctrine and glossary text: the revise and revoke lifecycle wording, and definitions for **Drift** and **Outside usage** for `docs/ccgf/CONTEXT.md`. Nothing is built and nothing in the doctrine is changed without the user's go-ahead.

The spec must also carry the **closed list of machine reason strings** and the projection-label wording that [What readers say about a withheld term](09-what-readers-say-about-a-withheld-term.md) settled, since the loader writes them and the readers show them.
