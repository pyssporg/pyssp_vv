---
id: INFO-004
type: info
title: Assessment Schema
summary: "Field rules for an assessment: one factor, its held constants, and its oracles with versioned policies."
date: 2026-10-22
status: current
pb_exempt: true
---

# Assessment Schema

Schema version `0.1.0`, written as `schema_version` and defaulted from the
package schema version.

An assessment declares one controlled comparison: what varies, what is held
constant, and which policies judge it.

## Fields

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `schema_version` | string | no | defaults to the package schema version |
| `assessment_id` | string | yes | stable, human-readable |
| `model` | string | yes | model or system under verification |
| `case` | string | yes | named scenario within the model |
| `factor` | object | yes | exactly one independent variable |
| `held` | list of string | yes | factors claimed constant; unique; must not contain the factor name |
| `oracles` | list of object | yes | at least one |

Unknown keys are rejected at every level.

## `factor`

| Field | Type | Rule |
| --- | --- | --- |
| `name` | string | must not appear in `held` |
| `levels` | list of string | at least one, no duplicates |

Two or more levels are required for a comparison. One level is a single
observation.

## `oracles[]`

| Field | Type | Rule |
| --- | --- | --- |
| `oracle_id` | string | unique within the assessment |
| `kind` | string | `cross_engine`, `reference_csv`, `analytic`, `invariant`, `metamorphic`, `measurement` |
| `policy` | object | see below |
| `params` | object | oracle-specific, JSON-safe |

## `policy`

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `comparison` | object | see below | how to measure |
| `criterion` | object | required | what difference is acceptable |
| `sufficiency` | object | `{}` | when the comparison is unfit to judge |
| `schema_version` | string | package version | policy schema |

### `comparison`

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `interpolation` | `linear` \| `step` | `linear` | `step` is the correct default for discrete outputs |
| `extrapolation` | `clamp` \| `nan` | `clamp` | what happens outside the source range |
| `shift_samples` | integer | `0` | symmetric lag search window |
| `max_gap_samples` | integer \| null | `0` | consecutive invalid samples that may be interpolated across; `null` interpolates across any gap |
| `normalisation` | `reference_peak` \| `reference_range` \| `unit` | `reference_peak` | denominator for normalised metrics |
| `grid` | `[start, stop, step]` \| null | `null` | explicit grid; `null` uses the reference samples |

### `criterion`

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `atol` | number | — | absolute allowance, non-negative |
| `rtol` | number | `0.0` | relative allowance, scaled by the reference peak |
| `kind` | `band` \| `equivalence` | `band` | `equivalence` reads the same limit as a pre-registered margin |
| `metric` | `max_abs_error` \| `mean_abs_error` \| `rmse` \| `normalised_max_abs_error` | `max_abs_error` | which number is judged |

### `sufficiency`

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `min_coverage` | number in [0, 1] | `0.0` | below this the comparison is `invalid` |
| `degenerate_range` | number | `0.0` | reference range at or below this cannot support an absolute criterion |
| `reject_shift_at_boundary` | boolean | `true` | a best shift at the search edge is `invalid` |

## Example

```json
{
  "schema_version": "0.1.0",
  "assessment_id": "BouncingBall/baseline",
  "model": "BouncingBall",
  "case": "baseline",
  "factor": {"name": "engine", "levels": ["ssp4sim", "omsimulator"]},
  "held": ["window", "step_size", "param_set"],
  "oracles": [
    {
      "oracle_id": "agreement",
      "kind": "cross_engine",
      "policy": {
        "comparison": {"interpolation": "linear", "shift_samples": 2, "max_gap_samples": 0},
        "criterion": {"atol": 0.001, "rtol": 0.01, "kind": "band", "metric": "max_abs_error"},
        "sufficiency": {"min_coverage": 0.95, "degenerate_range": 1e-12}
      },
      "params": {}
    }
  ]
}
```

## Rules that are not obvious

- `cross_engine` measures *agreement*. A `pass` means two implementations behave
  alike, not that either is correct.
- `equivalence` requires a criterion fixed before the data is seen. A margin
  chosen afterwards is not a criterion.
- `max_gap_samples: 0` is the honest default. Interpolating across a gap raises
  the apparent quality of the match without changing the model.
