---
id: INFO-006
type: info
title: Asset Map
summary: Which module, file, and public symbol realizes each architecture concern.
date: 2026-10-27
status: current
---

# Asset Map

Four module packages plus a version module, one Python distribution.

## Module packages

| Package | Files | Holds |
| --- | --- | --- |
| `policy` | `__init__.py` | `Policy`, `Criterion`, `CriterionKind`, `MetricName`, `ComparisonPolicy`, `Sufficiency` |
| `measure` | `series.py`, `alignment.py`, `metrics.py`, `figures.py` | `Trajectory`, `Grid`, `Alignment`, `Interpolation`, `Extrapolation`, `SignalMetrics`, `Comparison`, `FigureSpec` |
| `judge` | `verdict.py`, `criteria.py`, `judge.py`, `assessment.py`, `protocol.py` | `Verdict`, `MetricView`, `Reason`, `SignalJudgment`, `Judgment`, `Factor`, `OracleRef`, `Disposition`, `Assessment`, `Oracle`, `OracleContext`, `Candidate`, `Provenance` |
| `evidence` | `bundle.py`, `environment.py`, `hashing.py`, `metrics.py` | `EvidenceBundle`, `InputRef`, `VerdictRecord`, `MetricRow`, `ComparisonSummary` |

## Entry points

| Function | Module | Purpose |
| --- | --- | --- |
| `compare` | `measure.metrics` | One reference/candidate pair, all selected signals |
| `compare_many` | `measure.metrics` | Many candidates against one reference |
| `metric_rows` | `measure.metrics` | Comparison to metric-table rows |
| `build_figure_spec`, `render_figure` | `measure.figures` | Figure specification, then rendering |
| `judge`, `judge_signal` | `judge.judge` | Metric views to a verdict with reasons |
| `fingerprint` | `evidence.environment` | Environment record for a bundle |
| `digest_path` | `evidence.hashing` | Content digest of an input |
| `write_metric_csv`, `read_metric_csv`, `summarize_rows` | `evidence.metrics` | Metric table on disk |

## Version

`version.py` holds `SCHEMA_VERSION`, the schema version written into assessment
policies and evidence bundles. The package version in `pyproject.toml` moves
independently of it.

## Dependencies

No runtime dependencies. Extras add `numpy` (`measure`), `matplotlib`
(`figures`), `pint` (`units`).

## Owns
- Which concrete module and public symbol realizes which architecture concern.

## Excludes
- Which import each module may take: INFO-002.
- Install commands and CI: INFO-009.
