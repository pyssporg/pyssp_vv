---
id: INFO-002
type: info
title: Module Shape And Import Rules
summary: Module shape, the public library border, and which import each layer may take.
date: 2026-10-23
status: current
---

# Module Shape And Import Rules

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

`measure`'s module-level imports are numpy only. `matplotlib` is imported inside
`render_figure`, behind the `figures` extra; importing `measure` never loads it.
`policy`, `judge`, and `evidence` are standard-library only. Nothing here imports
another pyssp project.

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
| `measure` | stdlib, numpy, `pyssp_vv` | matplotlib at module level (allowed inside `render_figure`), any `pyssp_*` |
| `judge` | `policy`, `evidence` | `measure` |

The last rule is the important one: judgment consumes a **metric table** (a
structural protocol), not a trajectory. That is what makes the whole judgment
layer testable with fabricated numbers, without a simulation or a numeric
library.

Enforced by `tests/test_layering.py`.
