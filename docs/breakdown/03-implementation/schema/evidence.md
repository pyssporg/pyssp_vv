# Evidence Schema (`0.1.0`)

An evidence bundle is the durable result of running one assessment. It names its
inputs by digest, records the environment, and lists one verdict per oracle. It
contains no trajectories and no live objects.

## Fields

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `schema_version` | string | yes | written by the producer |
| `assessment_id` | string | yes | matches the assessment that produced it |
| `created` | string | yes | ISO-8601 UTC timestamp with offset |
| `environment` | object | yes | `pyssp_vv.evidence.environment.fingerprint()` |
| `inputs` | list of object | yes | may be empty only when no artifact inputs exist |
| `verdicts` | list of object | yes | one entry per declared oracle |

## `inputs[]`

| Field | Type | Rule |
| --- | --- | --- |
| `role` | string | what the input is for (`ssp_root`, `result_csv`, `reference`, …) |
| `path` | string | relative to the bundle file when inside its tree, else absolute |
| `sha256` | string | `sha256:<hex>`; for a directory, over sorted relative paths and contents |

A directory digest changes if a file is added, removed, renamed, or modified.
Moving the tree does not change it.

## `verdicts[]`

| Field | Type | Rule |
| --- | --- | --- |
| `oracle_id` | string | matches an `oracles[].oracle_id` in the assessment |
| `kind` | string | matches the oracle kind |
| `verdict` | string | `pass`, `fail`, `invalid`, `blocked`, `waived` |
| `metrics` | object | numeric only; non-numeric values are rejected before writing |
| `reasons` | list of string | machine-readable reason codes |

## Example

```json
{
  "schema_version": "0.1.0",
  "assessment_id": "BouncingBall/baseline",
  "created": "2026-10-22T09:14:02.113+00:00",
  "environment": {
    "python": "3.10.12",
    "platform": "Linux-6.8.0-x86_64",
    "distributions": {"pyssp-simulate": "0.1.1", "OMSimulator": null}
  },
  "inputs": [
    {"role": "result_csv", "path": "runs/ssp4sim/result.csv", "sha256": "sha256:1f0c…"}
  ],
  "verdicts": [
    {
      "oracle_id": "agreement",
      "kind": "cross_engine",
      "verdict": "invalid",
      "metrics": {"coverage": 0.42},
      "reasons": ["coverage-below-minimum"]
    }
  ]
}
```

## Rules that are not obvious

- `invalid` is a legitimate result: the comparison was not fit to judge, not the
  model wrong.
- A missing distribution is recorded as `null`, not omitted, so "same version"
  and "not installed" stay distinguishable.
- Metrics must be plain numbers. Anything richer belongs in the run artifacts
  the bundle points at.
