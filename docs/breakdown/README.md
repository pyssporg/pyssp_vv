# Product Breakdown — pyssp_vv

Current state of the V&V capability, for authors and consumers of the package.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- [00-intent](00-intent/README.md)
- [01-product](01-product/README.md)
- [02-architecture](02-architecture/README.md)
- [03-implementation](03-implementation/README.md)
- [04-verification](04-verification/README.md)
- [05-operation](05-operation/README.md)
- [06-evolution](06-evolution/README.md)
<!-- pb:index:end -->

## The Seven Layers

- `00-intent/` — why does the project exist, who is it for?
- `01-product/` — what is delivered, out of scope?
- `02-architecture/` — how are deliverables, evidence, and work organized?
- `03-implementation/` — with what concrete assets is it realized?
- `04-verification/` — how do we know it satisfies the requirements?
- `05-operation/` — how do authors run, maintain, release?
- `06-evolution/` — what controlled changes come next?
- the decision archive (`docs/archive/archive.zip`) — the flat, dated decision stream: history, never current state; read via `pb archive`, never browsed

## Boundary Rule

A document's home is the layer whose question it answers; information flows
downward only. Current state lives in the layer leaves, history in the decision
archive (`docs/archive/archive.zip`, read via `pb archive`), tracking in the
generated registers (`design-choice-log.md`, `traceability-map.md`) — this file
indexes current state only.

## Reading Order

Top-level index, then the layer index, then the leaf that owns the concern:

- `00-intent/README.md`
- `01-product/README.md`
- `02-architecture/README.md`
- `03-implementation/README.md`
- `04-verification/README.md`
- `05-operation/README.md`
- `06-evolution/README.md`

## Excludes

- Implementation detail and durable rationale: `docs/` (runtime-coupled), outside this tree
