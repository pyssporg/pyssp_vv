---
id: INFO-009
type: info
title: Install And CI
summary: Install paths, dependencies, local commands, and what CI executes.
date: 2026-10-27
status: current
---

# Install And CI

## Install

```bash
pip install -e ".[dev]"
```

Python >= 3.11.

## Dependencies

| Install | Provides |
| --- | --- |
| base | `policy`, `judge`, `evidence`, and the numpy-backed `measure` |
| `dev` | pytest, numpy, ruff |

## Local commands

```bash
python -m pytest -m "not slow"   # CI selection; drop the marker for the full suite
ruff check src tests            # line length 100, target py311
```

## CI

`.github/workflows/tests.yml` runs on push to `main` and on every pull request.

- One job, matrix over Python `3.11`, `3.12`; `fail-fast: false`.
- Steps: checkout, setup-python, `pip install -e ".[dev]"`, `ruff check src
  tests`, `python -m pytest -m "not slow"`, the contracts-import step, and a
  clean-checkout step.
- The contracts step imports `pyssp_vv.judge`, `pyssp_vv.policy`, and
  `pyssp_vv.evidence`, then asserts none of `numpy`, `matplotlib`, or `pint` is
  in `sys.modules`.

CI runs the same ruff command as the local lint gate.

## Owns
- Install paths, dependencies, local commands, and what CI executes.

## Excludes
- Why the contracts carry no dependencies: INFO-008.
- Schema version coupling: INFO-010.
