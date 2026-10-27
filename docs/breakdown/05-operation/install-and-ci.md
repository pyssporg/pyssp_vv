---
id: INFO-009
type: info
title: Install And CI
summary: Install paths, dependency extras, local commands, and what CI executes.
date: 2026-10-27
status: current
---

# Install And CI

## Install

```bash
pip install -e ".[dev]"          # contracts, standard library only
pip install -e ".[dev,measure]"  # measurement (numpy)
```

Python >= 3.10.

## Extras

| Extra | Provides |
| --- | --- |
| — | `policy`, `judge`, `evidence` |
| `measure` | trajectories, alignment, metrics, coverage |
| `figures` | rendering of the figure specification |
| `units` | pint-based unit checking (planned) |
| `all` | numpy, matplotlib, pint |
| `dev` | pytest, numpy, ruff |

## Local commands

```bash
python -m pytest          # full suite, pythonpath from pyproject
ruff check src tests      # line length 100, target py310
```

## CI

`.github/workflows/ci.yml` runs on push to `main` and on every pull request.

- One job, matrix over Python `3.10`, `3.11`, `3.12`; `fail-fast: false`.
- Steps: checkout, setup-python, `pip install -e ".[dev]"`, `python -m pytest`.
- A final step imports `pyssp_vv.judge`, `pyssp_vv.policy`, and
  `pyssp_vv.evidence`, then asserts none of `numpy`, `matplotlib`, `pint` is in
  `sys.modules`.

CI does not run ruff, the figure extra, or the units extra.

## Owns
- Install paths, extras, local commands, and what CI executes.

## Excludes
- Why the contracts carry no dependencies: INFO-008.
- Schema version coupling: INFO-010.
