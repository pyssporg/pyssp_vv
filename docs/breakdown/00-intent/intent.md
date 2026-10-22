# Intent

## Purpose

`pyssp_vv` is the V&V capability for simulation models. It provides two things
and keeps them apart:

- **measurement** — how far apart two trajectories are, under an explicit
  alignment and normalisation policy;
- **judgment** — whether that difference is acceptable, and why.

A claim is expressed as an assessment: one independent factor, the factors held
constant across its levels, and one or more oracles, each carrying a versioned
policy. Running an assessment produces an evidence bundle.

## Two kinds of claim

| Claim | Question | Oracles |
| --- | --- | --- |
| Verification | Does the implementation behave as specified? | agreement, reference trajectory, analytic solution, invariant, metamorphic relation |
| Validation | Is the model adequate for an intended use? | measured data, judged against a criterion fixed in advance |

## Commitments

- **Measurement and judgment are separate.** A metric is not a verdict. The
  measurement layer never returns an acceptance decision.
- **Numbers carry their policy.** Every metric is reported with the grid,
  interpolation, coverage, and denominator that produced it.
- **Comparisons are controlled or invalid.** A comparison that is not fit to be
  judged is `invalid`, never `fail`.
- **Claims are stated before evidence.** The criterion is part of the policy,
  recorded before the measurement runs.
- **Inputs are read-only and identified by digest.**
- **The capability is at the bottom of the dependency graph.** No other pyssp
  project is imported here; consumers depend on this package, not the reverse.

## Non-goals

- **Not a workflow engine.** Composition, scheduling, and node graphs belong to
  `pyssp_workflow` and the flow engine it uses.
- **Not a simulation substrate.** Running engines and normalising their output
  belongs to `pyssp_simulate`.
- **Not a plotting product.** Figures are derived views, never acceptance
  criteria.
- **Not a certifier.** A bundle supports a decision; it does not make it.

## Roles of the ecosystem

| Package | Responsibility | Depends on `pyssp_vv` |
| --- | --- | --- |
| `pyssp_vv` | measurement, judgment, evidence | — |
| `pyssp_simulate` | run engines, normalise results | `pyssp_vv.measure`, internally only |
| `pyssp_workflow` | build/run/compare/verify flows as nodes | whole package |
