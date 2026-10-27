---
id: INFO-007
type: info
title: Test Suite Map
summary: What each test file proves and how the suite runs.
date: 2026-10-27
status: current
---

# Test Suite Map

`tests/` holds the whole suite. `pyproject.toml` sets `pythonpath = ["src"]`,
`testpaths = ["tests"]`, `addopts = "-q"`, and `xfail_strict = true`.

Run with `python -m pytest`.

## Coverage per file

| File | Proves |
| --- | --- |
| `test_measure.py` | Resampling, comparison over a trajectory pair, normalisation, the comparison table, local shift errors, metric rows. Numeric expectations inherited from the upstream port. |
| `test_judge.py` | Judgment from fabricated metric tables: pass, fail with reason, rtol scaling, invalid on low coverage, degenerate reference, boundary shift, non-finite metric, no comparable samples, pessimistic aggregation, invalid dominating failure. No simulation, no numeric library. |
| `test_policy.py` | Policies and assessments round-trip as JSON and reject nonsense: unknown keys, a factor held constant, a negative criterion, out-of-range sufficiency, an assessment without an oracle. |
| `test_evidence.py` | Bundle round-trip, relative paths, directory digests tracking content, non-JSON metrics refused before writing, metric CSV, summary rows. |
| `test_figures.py` | Figure specification as data, and the matplotlib adapter behind the extra. |
| `test_layering.py` | The import graph: contract layers stdlib-only, measure numpy-only, declared extras, no pyssp project, judge independent of measure. |

## Shape of the suite

- Measurement is tested with numpy present.
- Judgment, policy, and evidence run without numpy or matplotlib.
- Two layering tests run a fresh interpreter and assert no heavy module is
  loaded on import.
- `xfail_strict = true` turns an unexpected pass into a failure.

## Owns
- What each test file covers.

## Excludes
- The import rules themselves: INFO-008.
- How CI invokes the suite: INFO-009.
