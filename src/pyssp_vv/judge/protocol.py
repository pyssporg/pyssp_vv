"""The oracle protocol: where a verdict may come from.

Provenance is part of the contract. ``AGREEMENT`` is engine-versus-engine
comparison; it records that two implementations differ (or do not), never that
either is correct, because shared bugs are invisible to it.

An oracle receives paths and read-only context. It may not read authoring
intermediates and may not modify inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping, Protocol, runtime_checkable

from pyssp_vv.judge.verdict import Verdict


class Provenance(str, Enum):
    AGREEMENT = "agreement"
    REFERENCE = "reference"
    ANALYTIC = "analytic"
    INVARIANT = "invariant"
    METAMORPHIC = "metamorphic"
    MEASUREMENT = "measurement"


@dataclass(frozen=True)
class Candidate:
    """One simulation output, addressed by path."""

    run_dir: Path
    result_csv: Path


@dataclass(frozen=True)
class OracleContext:
    """Assessment-level facts an oracle may read. Deliberately closed."""

    assessment_id: str
    held_factors: Mapping[str, str]
    reference: Path | None = None


@dataclass(frozen=True)
class OracleResult:
    oracle_id: str
    verdict: Verdict
    metrics: Mapping[str, float] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()


@runtime_checkable
class Oracle(Protocol):
    kind: str
    provenance: Provenance

    def evaluate(self, candidate: Candidate, context: OracleContext) -> OracleResult:
        """Render one verdict for ``candidate``."""
