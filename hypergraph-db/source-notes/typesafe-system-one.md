# Source note: TypeSafe's "System One" models and Jev

This is a **source note**, not a claim. It is background for the `System One` (scope `TypeSafe`) **Outside usage** in the prototype
hypergraph store. Nothing in the store depends on it, and nothing here has passed CCGF admission. It is a vendor's own description of
its product, kept so a human reviewing the collision claims can see what "System One" means outside CHI.

| | |
|---|---|
| Source | https://typesafe.ai/blog/introducing-system-one-models-and-jev |
| Title | "Introducing System One Models & Jev" (TypeSafe AI Blog, Company News) |
| Author, date | Diogo Almeida, founder of TypeSafe; posted Sep 15, 2026 |
| Retrieved | 2026-09-20 |
| How | Summarized by a model, then the figures below were **checked against the raw page text**. Everything else is paraphrase; quotes are short and verbatim. |

## What the page says

* **System One models** are a model class for automation inside software. **Jev** is TypeSafe's first, "available today in early
  access". The page's own one-line description: "a frontier-intelligence function call: unstructured state in, typed probabilistic
  decisions out."
* **Name.** Inspired by Kahneman's *Thinking, Fast and Slow*: the class name "draws on the distinction between fast, intuitive System 1
  thinking and slow, deliberate System 2 reasoning."
* **Input / output.** Text and program state in; type-safe structured values out, with possible outputs and structure defined in advance,
  and calibrated probabilities and confidence scores on every answer. It gives up free-form strings.
* **Method.** A new model architecture, a parallel sampler (all outputs in one query, not token by token) and a training method called
  Reinforcement Learning for Calibrated Decisions (RLCD).
* **Speed.** 70 ms to 500 ms end to end, which it says is 40x to 200x faster than frontier LLMs for "System One shaped queries"
  (it puts frontier models at 3 to 329 seconds). The timings were run from laptops on the West Coast, where the service is based.
* **Cost.** Input $0.042 per million tokens; output tokens "FREE (too cheap to meter)". It compares LLM input at $0.20 to $10 per
  million and output at about 5x input.
* **Uses named.** Workflows and conditional logic, map-reduce over datasets, real-time work under 100 ms, guardrailing LLM output,
  classification, routing, scoring and extraction.
* **Availability.** Early access, adding developers off a waitlist "as quickly as we can".

## Caveats (from the page and from checking it)

* These are **vendor claims**. "Can't hallucinate" and "no type errors" are the vendor's wording; the page argues the type-error
  claim is guaranteed by construction and asks for evidence on its bolder ones. None of it was independently tested here.
* On price the author writes that they "can't prove it isn't subsidized" and expect prices to go down. It is not described as
  non-subsidized.
* The page gives no model size, training data, or standard public benchmarks.

## How it relates to the CHI glossary

* `CONTEXT-MAP.md` says CHI's *System 1 / System 2* is "an authority split between generating and adjudicating, not TypeSafe's
  'System One' models, which the gate calls for judgments". The page is consistent with that: System One is a model product that returns
  probabilities for one decision, which is how the permission gate uses it (a *Signal*). CHI's split is about who may propose and who
  may admit.
* In the store: `System One` (Outside usage, scope `TypeSafe`) is the object of two `must not be confused with` claims, from
  *Generative layer (System 1)* and *Adjudication layer (System 2)*. Both are admitted, and their only evidence is the map line.
* If a fact from this page is ever wanted as a claim in the store, it needs its own extraction and human verification like any other
  evidence: a summary of a web page is candidate evidence, never admitted by being written down here.
