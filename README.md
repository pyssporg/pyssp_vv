# `pyssp_vv`

Verification and validation for simulation models.

Two capabilities, one distribution:

```text
measure/                     judge/
series, alignment,           roles, criterion, sufficiency,
metrics, coverage,           dispositions, verdicts
normalisation, figures
        │                            │
        └────────► policy ◄──────────┘
                     │
                 evidence
```

`measure` answers *how far apart* two trajectories are. `judge` answers
*is that acceptable, and why*. Neither answers the other's question, and the
split is enforced by tests rather than convention.

## Why judgment is separate from measurement

A metric is not a verdict. RMSE `0.014` says nothing until you know the grid it
was computed on, how much of the data was comparable, which denominator
normalised it, and which criterion judged it. This library keeps those as
explicit, versioned data and reports them beside every number.

More importantly, three ways a comparison can mislead are checked *before* the
criterion:

1. **Preconditions** — are the two sides comparable at all?
2. **Sufficiency** — could this test have failed? Low coverage, a degenerate
   expectation, or a shift that hit the search boundary make the comparison
   unfit to judge.
3. **Criterion** — only then is the declared margin applied.

A comparison that fails 1 or 2 is `invalid`, never `fail`. `invalid` means the
comparison was not legal; the correct response is to fix the comparison, not the
tolerance.

## Scope

**Verification** compares a simulation against an expectation that shares its
form: another engine, a reference trajectory, an analytical solution, an
invariant, a metamorphic relation. Agreement between engines is recorded as
*agreement*, never as *correctness* — shared bugs are invisible to it.

**Validation** compares a model against measured data under an intended use. It
needs three things verification does not: an intended-use statement, measured
data with uncertainty, and a criterion fixed before the comparison runs.

This library does not decide fitness for use and does not certify an engine. It
produces measurements and judgments with reasons, which is what a reviewer
needs and what a claim is made of.

## Install

```bash
pip install -e ".[dev]"          # contracts, standard library only
pip install -e ".[dev,measure]"  # measurement (numpy)
```

Extras: `measure`, `figures`, `units`, `all`.

## Use

```python
import numpy as np
from pyssp_vv.measure import Trajectory, compare
from pyssp_vv.judge import judge
from pyssp_vv.policy import Criterion, Policy, Sufficiency

reference = Trajectory(np.array([0.0, 1.0]), {"h": np.array([1.0, 0.5])}, label="ref")
candidate = Trajectory(np.array([0.0, 1.0]), {"h": np.array([1.0, 0.6])}, label="fmpy")

policy = Policy(
    criterion=Criterion(atol=0.05),
    sufficiency=Sufficiency(min_coverage=0.95),
)

comparison = compare(reference, candidate)
judgment = judge(comparison.signals, policy)

judgment.verdict        # Verdict.FAIL
judgment.reasons        # (Reason('criterion-exceeded', '0.1 > 0.05 (max_abs_error)'),)
```

## Status

`0.1.0`, alpha. Implemented: trajectories, alignment (linear and step
interpolation, clamp/NaN extrapolation, shift search), metric families,
coverage, normalisation, policy, judgment with reason codes, evidence bundles.
Figure specification is documented but not built.

## Documentation

- [Product breakdown](docs/breakdown/README.md) — intent, capabilities,
  architecture, schemas, verification, operation, and the decision archive
