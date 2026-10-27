---
id: CP-001
type: capability
title: Reported Numbers Carry Their Policy
summary: A metric is meaningful only together with the grid, coverage, denominator, and criterion that produced it.
date: 2026-10-27
status: current
---

# Reported Numbers Carry Their Policy

A metric is not a verdict.

RMSE `0.014` says nothing until the reader knows:

- the grid it was computed on;
- how much of the data was comparable;
- which denominator normalised it;
- which criterion judged it.

The library keeps those four as explicit, versioned data and reports them beside
every number.

## Owns
- The rule that a measurement is only meaningful together with its policy.

## Excludes
- The measurement mechanics that produce grid and coverage: INFO-003.
- The schemas that carry the policy to disk: INFO-004, INFO-005.
