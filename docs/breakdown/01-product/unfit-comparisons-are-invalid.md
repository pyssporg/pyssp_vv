---
id: CP-002
type: capability
title: Unfit Comparisons Are Invalid, Never Fail
summary: A comparison that fails preconditions or sufficiency is invalid; the fix is the comparison, not the tolerance.
date: 2026-10-27
status: current
---

# Unfit Comparisons Are Invalid, Never Fail

Three ways a comparison misleads are checked before the criterion applies:

1. **Preconditions** — are the two sides comparable at all?
2. **Sufficiency** — could this test have failed? Low coverage, a degenerate
   expectation, or a shift that hit the search boundary make the comparison
   unfit to judge.
3. **Criterion** — only then is the declared margin applied.

A comparison that fails step 1 or 2 is `invalid`, never `fail`.

`invalid` means the comparison was not legal. The correct response is to fix the
comparison, not the tolerance.

## Owns
- The distinction between an illegal comparison and a model defect.

## Excludes
- Step order and return values: INFO-003.
- The verdict vocabulary shared with evidence bundles: INFO-005.
