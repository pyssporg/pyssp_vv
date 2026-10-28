# Tests

Run from the package root:

```bash
python -m pytest
```

The package sets `pythonpath = ["src"]`; `tests/` is importable because pytest
inserts the test root, so `conftest.py` imports the local `fixture_guard`
module directly.

## Layout

| Path | Contents |
|---|---|
| `tests/test_*.py` | the suite, one file per subject |
| `tests/fixture_guard.py` | session-start/finish digest check over the test tree |
| `tests/conftest.py` | level markers and guard hooks |

## Fixture policy

- **Inline minimal CSVs and XML are deliberate unit inputs.** A two-row
  trajectory or a three-element SSD in a test function documents the input
  that the assertion depends on, and nothing else uses it.
- **Reuse promotes to a case directory.** Anything a second test needs becomes
  `tests/fixtures/<case>/input.<ext>` with a `case.md` recording provenance,
  the fault the case pins, the independent oracle, and the update policy.
  Case records follow the sibling `pyssp_simulate` suite's shape.
- **A test never writes into the checkout.** Every write target is derived
  from a `tmp_path` argument. `tests/test_fixture_policy.py` parses the test
  modules and fails on a literal-path write, on a write in a function with no
  `tmp_path` argument, and on any `tmp_path`-free write that is not listed
  there with a reason.

## Guard

`tests/fixture_guard.py` digests the whole `tests/` tree at session start and
again at session finish (excluding `__pycache__` and `*.pyc`). If a test wrote
a CSV, XML, or any other file next to the test modules instead of into
`tmp_path`, the session exits non-zero and lists the changed paths.

## Levels

Every test carries exactly one level marker. `tests/conftest.py` applies the
file default from `LEVEL_BY_FILE`; `tests/test_layering.py` asserts the
invariant.

| Level | Command |
|---|---|
| static | `python -m pytest -m level_static` |
| unit | `python -m pytest -m level_unit` |
| component | `python -m pytest -m level_component` |
| contract | `python -m pytest -m level_contract` |
| integration | `python -m pytest -m level_integration` |
| system | `python -m pytest -m level_system` |
| acceptance | `python -m pytest -m level_acceptance` |
| slow (opt-in) | `python -m pytest -m slow` |

## Adding a test file

Add the file to `LEVEL_BY_FILE` in `tests/conftest.py` so its tests receive the
file's level; the layering test fails otherwise. Lint with `ruff check tests`.
