---
id: CP-003
type: capability
title: Verification And Validation Claims
summary: Verification compares like forms and records agreement; validation compares measured data against a pre-registered criterion.
date: 2026-10-27
status: current
---

# Verification And Validation Claims

Two claims, two kinds of expectation.

**Verification** compares a simulation against an expectation that shares its
form:

- another engine;
- a reference trajectory;
- an analytical solution;
- an invariant;
- a metamorphic relation.

Agreement between engines is recorded as *agreement*, never as *correctness* —
shared bugs are invisible to it.

**Validation** compares a model against measured data under an intended use. It
needs three things verification does not:

- an intended-use statement;
- measured data with uncertainty;
- a criterion fixed before the comparison runs.

The library does not decide fitness for use and does not certify an engine. It
produces measurements and judgments with reasons: what a reviewer needs, and
what a claim is made of.

## Owns
- The scope boundary between verification and validation claims.

## Excludes
- Oracle kinds available to an assessment: INFO-004.
- The verdict a claim yields: INFO-003.
