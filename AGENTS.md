# AGENTS

## Rules

1. **Don't assume. Surface tradeoffs.** If a contract is ambiguous, stop and say
   so rather than picking a behaviour silently.
2. **Minimum code that solves the problem.** Nothing speculative.
3. **Touch only what you must.** Clean up only your own mess.
4. **Define success criteria and verify.**

## Hard constraints

- **`policy`, `judge`, and `evidence` are standard-library only.** They are the
  contracts and must install anywhere.
- **`measure` may use numpy and nothing else** beyond the contracts.
- **No other pyssp project may be imported.** `pyssp_vv` is the bottom of the
  dependency graph; `pyssp_simulate` and `pyssp_workflow` depend on it, never
  the reverse.
- **`judge` must not import `measure`.** Judgment consumes a metric table, not a
  trajectory. This is what makes it testable without simulation or numerics.
- **No verdicts in `measure`.** No `passed()`, no thresholds, no acceptance.
- **Explicit paths and plain data in public signatures.** No ambient working
  directory, no open handles.
- **Inputs are read-only.** Nothing writes to an input path; a verdict is
  derived from what was actually read.

`tests/test_layering.py` enforces the import rules. Fix the code, not the test.

## Conventions

- `docs/breakdown/` holds intent, architecture, schemas, and decisions.
- `ADR-<NNN>.md` architecture, `DD-<NNN>-<slug>.md` implementation,
  `ED-<NNN>-<slug>.md` evolution.
- Documentation states the contract; the docstring states the local rule.
