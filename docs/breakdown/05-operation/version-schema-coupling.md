---
id: INFO-010
type: info
title: Version Schema Coupling
summary: Package version and artifact schema version move independently; consumers read the schema version.
date: 2026-10-27
status: current
---

# Version Schema Coupling

Two version numbers, moved independently.

| Number | Home | Meaning |
| --- | --- | --- |
| package version | `pyproject.toml` `[project] version` | release of the distribution |
| `SCHEMA_VERSION` | `src/pyssp_vv/version.py` | shape of the artifacts the package writes |

Both read `0.1.0` today.

## Rules

- A patch release may add an optional field without a schema bump.
- Any breaking shape change bumps the schema major version.
- An assessment policy and an evidence bundle each carry `schema_version`.
- A consumer compares `schema_version`, not the package version, when it reads
  an artifact.

## Where the schema version appears

- `policy.schema_version` — policy object.
- `EvidenceBundle.schema_version` — written by the producer.
- Schema documents: INFO-004 (assessment), INFO-005 (evidence).

## Owns
- The independence of package version and artifact schema version.

## Excludes
- Field-by-field schema rules: INFO-004, INFO-005.
- Release procedure: INFO-009.
