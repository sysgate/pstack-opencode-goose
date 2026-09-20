# Proposed spec: the ambiguity allowance (item B4, decision D5)

**Superseded in two places (2026-09-20), see `prototype-hypergraph/DECISIONS.md`:** decision 6 replaced "the meanings" with *combinations* of meanings (one meaning for every bounded member), and decision 4 corrected the walk-through row below that says the hyperedge "returns to `PENDING`" when the term is narrowed to Beta. That is only true while it is still pending; an `ADMITTED` hyperedge becomes `CHALLENGED`. The applied doctrine text is current; the text below is history.

**Status (2026-09-19): APPLIED as drafted, with all four recommendations approved (human authority only, per binding, meanings named, lapse on narrowing). The text below is otherwise kept as written and is now history.**

One addition beyond the edit table: the table listed changes to existing lines but no definition of the allowance in the doctrine itself, so a short "Ambiguity Allowance" subsection was added to `AGENTS.md` (before "DSN Anti-Patterns") and a bullet to `ARCHITECTURE.md` §3, so the doctrine does not cite something it never defines. The glossary's DSN state entry now says "ambiguity allowance" instead of "recorded allowance".

D5 says evidence binds to narrowed terms, and to bounded-ambiguous ones only under a recorded allowance. The doctrine never defines that allowance, so four places still contradict each other and the state-vocabulary edit deliberately avoided mentioning it. This draft defines it.

## What it changes, and what it does not

- **The rule it bends:** "If 名界 fails, do not proceed to evidence admission" (`AGENTS.md:209`). A bounded-ambiguous term is a 名界 halt, so today no evidence may bind to a hyperedge that has such a member.
- **What an allowance does:** it lets one specific evidence binding proceed despite that halt, with the ambiguity carried forward. It does not narrow the term, does not admit anything, and does not change the term's DSN state.
- **What it does not touch:** `UNRESOLVED`, `CONFLICT` and `DENIED` terms never take evidence. Only `BOUNDED_AMBIGUOUS` (a known, explicit, finite set of meanings, D4) is eligible.

Evidence binds to a hyperedge (ADR 0001), not to a term. So an allowance is attached to a binding on a hyperedge that has a bounded-ambiguous member.

## The design (my recommendation for each choice)

1. **Who may grant it: a human authority only, in v1.** Never a generative-layer agent, and never the actor that proposed the binding. `Receipt.actor` already allows "system agent or human authority" (`ARCHITECTURE.md:365`); this narrows it for allowances. A pre-registered deterministic policy rule could be added later, but a rule is another thing to specify and to trust, so v1 does not have it.
2. **What it names:** the specific evidence, the specific hyperedge, the bounded-ambiguous member, and which of that member's remaining meanings the evidence is claimed to hold under. Covering all of them must be stated as such, not implied. A reason is required.
3. **Scope: one binding, not one term.** An allowance for one evidence record on one hyperedge authorizes nothing else: not a second evidence record, not another hyperedge using the same term.
4. **How it is recorded:** a receipt of a new type `AMBIGUITY_ALLOW`, decision `BOUND`, whose basis lists the meanings covered, the reason and the granting authority. The evidence binding gains `allowance_receipt_id: string | null`. No allowance, no binding.
5. **Lifetime: it lapses, it does not expire by time.** It lapses (the binding returns to being re-validated) when the term is narrowed or its set of meanings changes, and when the evidence or the hyperedge is revised or revoked.
6. **Downstream effect: the ambiguity stays visible.** A hyperedge with allowance-bound evidence carries the ambiguity in its uncertainty envelope, states which meanings the evidence covers, and is projected under the label `Bounded Ambiguous`, never plain `Admitted`.
7. **Fail closed:** a missing, malformed, lapsed, or wrongly granted allowance means the binding is refused, and the hyperedge stays `PENDING` with the DSN state as the failure reason.

## A concrete walk-through

The candidate "the Fund" has two known meanings, Alpha Fund and Beta Fund, so its DSN state is `BOUNDED_AMBIGUOUS`. The claim is a hyperedge of type `OBLIGATION`: "Party A owes the Fund a payment". The evidence is a bank statement showing a payment to Alpha only.

| Step | Outcome |
|---|---|
| Evidence proposed with no allowance | Refused. The hyperedge stays `PENDING`. |
| A generative-layer agent records an allowance | Refused: not a human authority. |
| The user grants an allowance covering {Alpha} only, reason "statement names Alpha" | Binding accepted. The hyperedge records that the evidence holds only under Alpha; the Beta meaning stays unsupported. Projected as `Bounded Ambiguous`. |
| Same allowance offered for a second statement | Refused: an allowance covers one binding. |
| Later, the term is narrowed to Alpha | The allowance lapses. The binding is re-validated as an ordinary `NARROWED` binding and passes if the evidence supports it. |
| The term is instead narrowed to Beta | The allowance lapses and the Alpha-only evidence no longer supports the claim: the hyperedge returns to `PENDING` with reason `UNSUPPORTED`. |

## Doctrine edits this would make (current line numbers)

| Where | Now | Change |
|---|---|---|
| `AGENTS.md:255` (DSN state table) | `Continue only with ambiguity annotation; do not hard-judge` | Add: evidence binding only under an ambiguity allowance |
| `AGENTS.md:279` (anti-patterns) | `Bind evidence to an ambiguous term.` | `Bind evidence to an ambiguous term without an ambiguity allowance.` |
| `AGENTS.md:1027` (required test) | `... or explicitly allowed BOUNDED_AMBIGUOUS` | `... or BOUNDED_AMBIGUOUS with a valid ambiguity allowance`, plus the tests below |
| `ARCHITECTURE.md:74-75` (DSN diagram) | Only `NARROWED` "Admissible to 據界" | `BOUNDED_AMBIGUOUS`: admissible to 據界 only per binding, under an allowance |
| `ARCHITECTURE.md:81` (DSN invariant) | Evidence never bound to `UNRESOLVED` or uncommitted term | Add: nor to `BOUNDED_AMBIGUOUS` without an allowance |
| `ARCHITECTURE.md` §9.1 | `HyperedgeEvidenceBinding`, receipt types | Add `allowance_receipt_id: string \| null`; add receipt type `AMBIGUITY_ALLOW` |
| `docs/ccgf/CONTEXT.md` | Bounded ambiguity entry | New term "Ambiguity allowance" |

`AGENTS.md` edits go to all four copies (the `chi-platform` one in place).

## Tests to require

- Evidence binding on a `BOUNDED_AMBIGUOUS` member fails without an allowance.
- It succeeds with a valid allowance, and the hyperedge carries the ambiguity in its uncertainty envelope and projects as `Bounded Ambiguous`.
- An allowance recorded by a generative-layer actor, or by the actor that proposed the binding, is refused.
- An allowance covers only its own binding and only the meanings it names.
- The allowance lapses when the term is narrowed, when the meaning set changes, and when the evidence or hyperedge is revised or revoked.
- `UNRESOLVED`, `CONFLICT` and `DENIED` terms never take evidence, allowance or not.

## Decisions for you (recommendation first)

1. **Human only, or also deterministic policy rules?** Recommend human only in v1: it is the strictest option, and CHI is a personal system where the human is the user.
2. **Per binding, or per term?** Recommend per binding. Per term would let one grant quietly authorize every later hyperedge that uses the term.
3. **Must the granter name the meanings covered?** Recommend yes: an allowance that says only "ambiguity accepted" defeats the point of a bounded set.
4. **Lapse on narrowing, or survive it?** Recommend lapse and re-validate: once the term is narrowed the ordinary rule applies and the allowance has no job left.

## Not covered

How the human grants an allowance in practice (UI, command, or file) is an implementation question and is left open. No code implements the hypergraph, so nothing needs to change outside the docs.
