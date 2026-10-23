# AGENTS

## Vision first (required)

Before you read code, edit files, or plan a change, read the project vision:

**`docs/breakdown/00-intent/intent.md`**

It states why this repository exists, what it commits to, and what it refuses to
become. It is the first document to read, not a reference of last resort.

- Read it in full before making any change to code, tests, docs, or artifacts.
- Judge every proposed change against it. If a change conflicts with the vision,
  its commitments, goals, or non-goals, stop and surface the conflict; do not
  implement it silently.
- If the work shows the long-term direction is wrong, change the vision
  deliberately first, then the code. Never let the repository drift away from
  its stated intent.

## Rules

1. **Don't assume. Surface tradeoffs.** If a contract is ambiguous, stop and say
   so rather than picking a behaviour silently.
2. **Minimum code that solves the problem.** Nothing speculative.
3. **Touch only what you must.** Clean up only your own mess.
4. **Define success criteria and verify.**

## Repository Focus

`pyssp_vv` is the V&V capability for simulation models. It measures how far
apart two trajectories are under an explicit alignment and normalisation policy,
and judges whether that difference is acceptable, with reasons. Measurement and
judgment stay separate, and a claim is stated before evidence is collected.

- Modules: `policy`, `measure`, `judge`, and `evidence`.
- It sits at the bottom of the pyssp dependency graph; consumers depend on it,
  never the reverse.

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

## Code guidelines

- Keep the public vocabulary small and stable: trajectory, comparison, metric,
  policy, judgment, verdict, evidence.
- Documentation states the contract; the docstring states the local rule.
- Prefer plain data and explicit arguments over implicit state.

## Conventions

- `docs/breakdown/` holds intent, architecture, schemas, and decisions.
- Decision records use `ADR-<NNN>.md` architecture, `DD-<NNN>-<slug>.md`
  implementation, and `ED-<NNN>-<slug>.md` evolution.

## Environment

- Python >= 3.10.
- Install: `pip install -e ".[dev]"` (contracts, standard library only); add
  `[measure]` for the numpy-backed measurement layer.
- Tests: `python -m pytest` (pyproject sets `pythonpath`); lint with
  `ruff check src tests` (line length 100, py310).
