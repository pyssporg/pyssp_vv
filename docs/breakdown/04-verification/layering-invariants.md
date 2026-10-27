---
id: INFO-008
type: info
title: Layering Invariants
summary: Import rules for the four module packages and the test that guards each one.
date: 2026-10-27
status: current
---

# Layering Invariants

Five rules, each guarded by a test in `tests/test_layering.py`. The test walks
every module under `src/pyssp_vv` with `ast`; fix the code, not the test.

## Rules

| Rule | Guard |
| --- | --- |
| `policy`, `judge`, `evidence` import stdlib only | `test_contract_layers_are_standard_library_only` |
| `measure`'s module-level imports are stdlib or numpy | `test_measure_uses_only_numpy_beyond_the_contracts` |
| `measure` function-local imports stay inside declared extras (`matplotlib`) | `test_measure_function_local_imports_stay_within_declared_extras` |
| No module imports another pyssp project | `test_no_pyssp_project_is_imported` |
| `judge` never imports `pyssp_vv.measure` | `test_judge_does_not_import_measure` |

## Load-time checks

Two tests run fresh interpreters with `src` importable:

- `test_importing_measure_does_not_load_matplotlib` imports
  `pyssp_vv.measure.figures` and asserts `matplotlib` is absent from
  `sys.modules`.
- `test_importing_evidence_does_not_load_numpy_or_matplotlib` imports
  `pyssp_vv.evidence.metrics` and asserts neither is loaded.

## Why these rules

`policy`, `judge`, and `evidence` are the contracts. They must install anywhere,
so a third-party import is a packaging defect, not a style issue.

`measure` may use numpy at module level. `matplotlib` sits behind the `figures`
extra and is imported inside `render_figure`, so a caller that never draws a
figure never pays for it.

`judge` consumes a metric table (a structural protocol), not a trajectory. That
is what makes the judgment layer testable with fabricated numbers, without a
simulation or a numeric library.

`pyssp_vv` is the bottom of the dependency graph. Consumers depend on it, never
the reverse.

## Owns
- The import boundary and its enforcement.

## Excludes
- The architecture concern behind each rule: INFO-002.
- The rest of the suite: INFO-007.
