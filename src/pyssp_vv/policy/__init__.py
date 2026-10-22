"""Policies: the versioned data a reviewer approves.

Three concerns, kept separate because they are decided by different people for
different reasons:

- :class:`ComparisonPolicy` — how two trajectories are put on a common grid.
- :class:`Criterion` — what difference is acceptable.
- :class:`Sufficiency` — when a comparison is not fit to be judged at all.

A tolerance is not an uncertainty. Keeping them apart is the point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from pyssp_vv.version import SCHEMA_VERSION


class CriterionKind(str, Enum):
    """How the acceptance margin is interpreted."""

    BAND = "band"
    EQUIVALENCE = "equivalence"


class MetricName(str, Enum):
    MAX_ABS = "max_abs_error"
    MEAN_ABS = "mean_abs_error"
    RMSE = "rmse"
    NORMALISED_MAX_ABS = "normalised_max_abs_error"


@dataclass(frozen=True)
class ComparisonPolicy:
    """How to put two trajectories on a common grid."""

    interpolation: str = "linear"
    extrapolation: str = "clamp"
    shift_samples: int = 0
    normalisation: str = "reference_peak"
    grid: tuple[float, float, float] | None = None
    max_gap_samples: int | None = 0

    def __post_init__(self) -> None:
        if self.interpolation not in ("linear", "step"):
            raise ValueError(f"Unknown interpolation {self.interpolation!r}")
        if self.extrapolation not in ("clamp", "nan"):
            raise ValueError(f"Unknown extrapolation {self.extrapolation!r}")
        if self.shift_samples < 0:
            raise ValueError("shift_samples must be non-negative")
        if self.max_gap_samples is not None and self.max_gap_samples < 0:
            raise ValueError("max_gap_samples must be non-negative or None")
        if self.grid is not None:
            start, stop, step = self.grid
            if stop <= start or step <= 0:
                raise ValueError("grid must be (start, stop, positive step) with stop > start")

    def to_dict(self) -> dict[str, Any]:
        return {
            "interpolation": self.interpolation,
            "extrapolation": self.extrapolation,
            "shift_samples": self.shift_samples,
            "normalisation": self.normalisation,
            "grid": list(self.grid) if self.grid is not None else None,
            "max_gap_samples": self.max_gap_samples,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ComparisonPolicy":
        grid = data.get("grid")
        return cls(
            interpolation=str(data.get("interpolation", "linear")),
            extrapolation=str(data.get("extrapolation", "clamp")),
            shift_samples=int(data.get("shift_samples", 0)),
            normalisation=str(data.get("normalisation", "reference_peak")),
            grid=tuple(float(value) for value in grid) if grid is not None else None,
            max_gap_samples=data.get("max_gap_samples", 0),
        )


@dataclass(frozen=True)
class Criterion:
    """The declared acceptance rule.

    ``limit`` is ``atol + rtol * reference_peak``. With ``kind="equivalence"``
    the same limit is treated as a pre-registered equivalence margin, which is
    the correct reading when comparing against measured data.
    """

    atol: float
    rtol: float = 0.0
    kind: CriterionKind = CriterionKind.BAND
    metric: MetricName = MetricName.MAX_ABS

    def __post_init__(self) -> None:
        if self.atol < 0 or self.rtol < 0:
            raise ValueError("Criterion values must be non-negative")

    def limit(self, reference_peak: float) -> float:
        return self.atol + self.rtol * max(abs(reference_peak), 0.0)

    def holds(self, value: float, reference_peak: float) -> bool:
        if not math.isfinite(value):
            return False
        return value <= self.limit(reference_peak)

    def to_dict(self) -> dict[str, Any]:
        return {
            "atol": self.atol,
            "rtol": self.rtol,
            "kind": CriterionKind(self.kind).value,
            "metric": MetricName(self.metric).value,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Criterion":
        return cls(
            atol=float(data["atol"]),
            rtol=float(data.get("rtol", 0.0)),
            kind=CriterionKind(data.get("kind", CriterionKind.BAND)),
            metric=MetricName(data.get("metric", MetricName.MAX_ABS)),
        )


@dataclass(frozen=True)
class Sufficiency:
    """Minimum conditions for a comparison to be worth judging.

    These are not tolerances. They protect against a metric that looks good
    because there was almost nothing to compare.
    """

    min_coverage: float = 0.0
    degenerate_range: float = 0.0
    reject_shift_at_boundary: bool = True

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_coverage <= 1.0:
            raise ValueError("min_coverage must be within [0, 1]")
        if self.degenerate_range < 0:
            raise ValueError("degenerate_range must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_coverage": self.min_coverage,
            "degenerate_range": self.degenerate_range,
            "reject_shift_at_boundary": self.reject_shift_at_boundary,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Sufficiency":
        return cls(
            min_coverage=float(data.get("min_coverage", 0.0)),
            degenerate_range=float(data.get("degenerate_range", 0.0)),
            reject_shift_at_boundary=bool(data.get("reject_shift_at_boundary", True)),
        )


@dataclass(frozen=True)
class Policy:
    """Everything needed to measure and judge one assessment, versioned."""

    comparison: ComparisonPolicy = ComparisonPolicy()
    criterion: Criterion = Criterion(atol=1e-6)
    sufficiency: Sufficiency = Sufficiency()
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "comparison": self.comparison.to_dict(),
            "criterion": self.criterion.to_dict(),
            "sufficiency": self.sufficiency.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Policy":
        return cls(
            comparison=ComparisonPolicy.from_dict(data.get("comparison", {})),
            criterion=Criterion.from_dict(data["criterion"]),
            sufficiency=Sufficiency.from_dict(data.get("sufficiency", {})),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )
