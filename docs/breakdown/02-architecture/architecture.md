# Architecture

## Shape

```text
measure/                    judge/
series, alignment,          policy, criterion,
metrics, coverage,          sufficiency, dispositions,
normalisation, figures      verdict, reasons
      │                             │
      └──────────► policy ◄─────────┘
                     │
                 evidence
```

`measure` imports numpy. `policy`, `judge`, and `evidence` are standard-library
only. Nothing here imports another pyssp project.

## Library boundary rule

This package sits at the bottom of the dependency graph. Its border is its
documented public surface, not its module tree: `Trajectory`, `Comparison`,
`SignalMetrics`, `Policy`, `Judgment`, `Verdict`, and `EvidenceBundle` may
cross to a consumer. Internal codecs, helpers, and private fields do not.
Standard artifacts remain the preferred interchange whenever a file contract
exists.

## Layers and import rules

| Layer | May import | Must not import |
| --- | --- | --- |
| `policy`, `judge`, `evidence` | stdlib, `pyssp_vv` | numpy, matplotlib, any `pyssp_*` |
| `measure` | stdlib, numpy, `pyssp_vv` | matplotlib at module level, any `pyssp_*` |
| `judge` | `policy`, `evidence` | `measure` |

The last rule is the important one: judgment consumes a **metric table** (a
structural protocol), not a trajectory. That is what makes the whole judgment
layer testable with fabricated numbers, without a simulation or a numeric
library.

Enforced by `tests/test_layering.py`.

## Measurement

- `Trajectory` is one time base plus named channels. Per-channel time bases are
  not modelled; callers resample first. That keeps every alignment decision
  visible.
- Alignment chooses the grid, the interpolation (`linear` or `step`), the
  extrapolation (`clamp` or `nan`), the shift search window, and the gap rule.
- The gap rule is not cosmetic. Interpolating across missing samples makes the
  error look better and the coverage look complete. A target that lands on an
  invalid sample, or strictly inside a gap wider than `max_gap_samples`, is not
  comparable and does not count towards coverage.
- Every metric carries `coverage`, `denominator`, `normalisation`, and the
  alignment that produced it.

## Judgment

Four steps, in order. A later step does not run if an earlier one fails.

1. **Preconditions** — the comparison has signals, samples, and finite values.
2. **Sufficiency** — could this test have failed? Coverage below the minimum, a
   degenerate expectation, or a shift at the search boundary make the comparison
   unfit to judge.
3. **Criterion** — the declared margin, evaluated on the selected metric.
4. **Disposition** — a recorded waiver, applied by the caller, converts a failure
   to `waived`. It never edits metrics.

`judge()` returns `pass`, `fail`, or `invalid`. `blocked` (no metrics could be
produced) and `waived` (disposition) are applied by the caller.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `pass` | The criterion holds |
| `fail` | The criterion is exceeded |
| `invalid` | The comparison was not fit to judge |
| `blocked` | Metrics could not be produced |
| `waived` | A recorded disposition overrides a failure |

`invalid` is load-bearing: without it, an uncontrolled comparison looks like a
model defect and the first response is to loosen a tolerance.

## Why the capability is a separate package

`pyssp_simulate` used to carry comparison. That gave it two reasons to change —
engines and analysis — and put acceptance-adjacent code (`passed()`, reference
CSV handling) in a substrate. Measurement now lives here, next to the judgment
that consumes it.

`pyssp_simulate` may import `pyssp_vv.measure` for its own convenience (a fast
comparison inside a permutation run). It must not re-export that surface, and it
must not import `pyssp_vv.judge`.

## Reporting

Figures are derived artifacts. The specification is data: overlay, residual
panel, criterion band, gap shading, shift indicator. Rendering sits behind the
`figures` extra. A figure is never hashed into evidence and never an acceptance
criterion.

## Packaging

| Extra | Provides |
| --- | --- |
| — | `policy`, `judge`, `evidence` |
| `measure` | trajectories, alignment, metrics, coverage |
| `figures` | rendering of the figure specification |
| `units` | pint-based unit checking (planned) |

## Open questions

1. **Policy containment.** Does an `Assessment` embed its policies, or reference
   them by id and digest? Currently embedded in `OracleRef.policy`.
2. **Criterion kind.** `band` and `equivalence` are both accepted. Only `band` is
   exercised today; the equivalence path needs a measured-data contract.
3. **Coverage definition.** Currently sample fraction. Time fraction can differ
   sharply for irregular sampling.
