# ED-001: Measurement and Judgment in One Package

**Status:** Accepted (measurement implemented; upstream extraction pending)
**Layer:** evolution-decision

---

## Context

Three options were considered for simulation-data comparison:

1. Extract a standalone comparison and plotting library, beside
   `pyssp_simulate.compare`.
2. Keep comparison in `pyssp_simulate` and add judgment on top.
3. Own measurement here, next to judgment, and remove it from the substrate.

Option 1 was rejected: it would have been a third implementation of the same
metrics, with a thin moat and a new release cadence.

Option 2 was rejected after inspection: `pyssp_simulate` exposed a `compare` CLI
and `PairReport.passed()`. Acceptance logic in a simulation substrate gives that
package a second reason to change, and the `ComparisonWindow` and reference-CSV
support added in 0.1.1 were requirements leaking in from a consumer. Nothing
outside `pyssp_simulate` imported that surface, so the extraction cost was one
internal module.

## Decision

One package, two modules.

- `pyssp_vv.measure` — series, alignment, metric families, normalisation,
  coverage, figures. Numeric; numpy behind an extra.
- `pyssp_vv.judge` — roles, criterion, sufficiency, dispositions, verdicts.
  Standard library only; consumes a metric table, not a trajectory.

Consumers:

| Package | May use | Must not |
| --- | --- | --- |
| `pyssp_simulate` | `pyssp_vv.measure`, internally | re-export it, or import `judge` |
| `pyssp_workflow` | the whole package | add measurement or judgment of its own |
| `pyssp_vv` | nothing from the ecosystem | import any other `pyssp_*` |

## Why the modules stay in one distribution

Splitting measurement and judgment into two packages would buy independent
release cadence at the cost of a cross-package version matrix and policy types
that reference each other. The module boundary is enforced by an import test, so
the separation is real without the packaging overhead. If a non-SSP consumer
appears, `measure` is already dependency-free of the pyssp family and can be cut
out mechanically.

## Consequences

- `pyssp_simulate` loses `compare`, the `compare` CLI subcommand, and the
  `PairReport.passed()` surface. Its permutations may still measure internally,
  but must not surface a verdict.
- Judgment is testable with fabricated metric tables: no simulation, no engines,
  no numpy.
- Coverage and the gap rule are first-class. Interpolating across missing samples
  raises apparent quality; a target inside a gap is not comparable and does not
  count towards coverage.
- A merge of the two modules would reintroduce the ambiguity this decision
  exists to remove. The import test is the guardrail.

## Open

- The upstream removal from `pyssp_simulate` needs its own ADR there.
- `ADR-005` in `ssp_references` cites cross-engine comparison as part of the
  substrate's rationale; it needs amending.
