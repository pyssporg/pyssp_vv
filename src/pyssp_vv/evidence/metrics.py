"""The metric table: one row per signal, and the comparison summary.

The table is a durable artifact, so it lives in the standard-library layer: a
reviewer tool or a CI check that reads ``metrics.csv`` must not install numpy.
The bridge from a measured comparison to these rows is
:func:`pyssp_vv.measure.metrics.metric_rows`, which owns the numerics.

Column names are the reviewed schema (EVAL-005) and are kept verbatim;
``run_a`` is the reference, ``run_b`` the candidate.
"""

from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

#: Declared column order of ``metrics.csv``, from signal outward to policy.
METRIC_COLUMNS: tuple[str, ...] = (
    "signal",
    "max_abs_error",
    "max_shift_abs_error",
    "mean_abs_error",
    "rmse",
    "run_a_label",
    "run_a_min",
    "run_a_max",
    "run_b_label",
    "run_b_min",
    "run_b_max",
    "coverage",
    "shift_samples",
    "normalisation",
    "denominator",
    "normalised_max_abs_error",
    "undefined",
)


@dataclass(frozen=True)
class MetricRow:
    """One signal's measured difference, as written to metrics.csv.

    Column names are the reviewed metric-row schema, versioned by
    ``pyssp_vv.version.SCHEMA_VERSION``; ``run_a`` is the reference, ``run_b``
    the candidate.
    """

    signal: str
    max_abs_error: float
    max_shift_abs_error: float
    mean_abs_error: float
    rmse: float
    run_a_label: str
    run_a_min: float
    run_a_max: float
    run_b_label: str
    run_b_min: float
    run_b_max: float
    coverage: float
    shift_samples: int
    normalisation: str
    denominator: float
    normalised_max_abs_error: float
    undefined: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Plain data; ``undefined`` joined with ';' as the CSV stores it."""
        return {
            "signal": self.signal,
            "max_abs_error": self.max_abs_error,
            "max_shift_abs_error": self.max_shift_abs_error,
            "mean_abs_error": self.mean_abs_error,
            "rmse": self.rmse,
            "run_a_label": self.run_a_label,
            "run_a_min": self.run_a_min,
            "run_a_max": self.run_a_max,
            "run_b_label": self.run_b_label,
            "run_b_min": self.run_b_min,
            "run_b_max": self.run_b_max,
            "coverage": self.coverage,
            "shift_samples": self.shift_samples,
            "normalisation": self.normalisation,
            "denominator": self.denominator,
            "normalised_max_abs_error": self.normalised_max_abs_error,
            "undefined": ";".join(self.undefined),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> MetricRow:
        undefined = data.get("undefined", "")
        if isinstance(undefined, str):
            names = tuple(part for part in undefined.split(";") if part)
        else:
            names = tuple(str(part) for part in undefined or ())
        return cls(
            signal=str(data["signal"]),
            max_abs_error=float(data["max_abs_error"]),
            max_shift_abs_error=float(data["max_shift_abs_error"]),
            mean_abs_error=float(data["mean_abs_error"]),
            rmse=float(data["rmse"]),
            run_a_label=str(data["run_a_label"]),
            run_a_min=float(data["run_a_min"]),
            run_a_max=float(data["run_a_max"]),
            run_b_label=str(data["run_b_label"]),
            run_b_min=float(data["run_b_min"]),
            run_b_max=float(data["run_b_max"]),
            coverage=float(data["coverage"]),
            shift_samples=int(data["shift_samples"]),
            normalisation=str(data["normalisation"]),
            denominator=float(data["denominator"]),
            normalised_max_abs_error=float(data["normalised_max_abs_error"]),
            undefined=names,
        )


@dataclass(frozen=True)
class ComparisonSummary:
    """One comparison as a manifest records it, above the per-signal rows."""

    run_a_label: str
    run_b_label: str
    time_points: int
    compared_signal_count: int
    max_abs_error: float
    max_shift_abs_error: float
    mean_abs_error: float
    rmse: float
    max_rel_error: float
    min_coverage: float

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "run_a_label": self.run_a_label,
            "run_b_label": self.run_b_label,
            "time_points": self.time_points,
            "compared_signal_count": self.compared_signal_count,
            "max_abs_error": self.max_abs_error,
            "max_shift_abs_error": self.max_shift_abs_error,
            "mean_abs_error": self.mean_abs_error,
            "rmse": self.rmse,
            "max_rel_error": self.max_rel_error,
            "min_coverage": self.min_coverage,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ComparisonSummary:
        return cls(
            run_a_label=str(data["run_a_label"]),
            run_b_label=str(data["run_b_label"]),
            time_points=int(data["time_points"]),
            compared_signal_count=int(data["compared_signal_count"]),
            max_abs_error=float(data["max_abs_error"]),
            max_shift_abs_error=float(data["max_shift_abs_error"]),
            mean_abs_error=float(data["mean_abs_error"]),
            rmse=float(data["rmse"]),
            max_rel_error=float(data["max_rel_error"]),
            min_coverage=float(data["min_coverage"]),
        )


def write_metric_csv(path: Path | str, rows: Sequence[MetricRow]) -> Path:
    """Write ``rows`` under :data:`METRIC_COLUMNS` and return the target path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(METRIC_COLUMNS), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())
    return target


def read_metric_csv(path: Path | str) -> tuple[MetricRow, ...]:
    """Read a metrics CSV written by :func:`write_metric_csv`."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in METRIC_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"metrics CSV is missing columns: {missing}")
        return tuple(MetricRow.from_dict(row) for row in reader)


def _mean(values: list[float], *, present: bool) -> float:
    if values:
        return statistics.fmean(values)
    return float("nan") if present else 0.0


def summarize_rows(rows: Sequence[MetricRow], *, time_points: int) -> ComparisonSummary:
    """Aggregate metric rows as the manifest summary does.

    ``mean_abs_error`` and ``rmse`` average the finite rows, ``max_rel_error``
    is the largest finite normalised error, and ``min_coverage`` the smallest
    coverage. Empty input yields zeros rather than an exception; the labels are
    taken from the first row, because one summary describes one comparison.
    """
    mean_values = [row.mean_abs_error for row in rows if math.isfinite(row.mean_abs_error)]
    rmse_values = [row.rmse for row in rows if math.isfinite(row.rmse)]
    relative_values = [
        row.normalised_max_abs_error
        for row in rows
        if math.isfinite(row.normalised_max_abs_error)
    ]
    return ComparisonSummary(
        run_a_label=rows[0].run_a_label if rows else "",
        run_b_label=rows[0].run_b_label if rows else "",
        time_points=int(time_points),
        compared_signal_count=len(rows),
        max_abs_error=max((row.max_abs_error for row in rows), default=0.0),
        max_shift_abs_error=max((row.max_shift_abs_error for row in rows), default=0.0),
        mean_abs_error=_mean(mean_values, present=bool(rows)),
        rmse=_mean(rmse_values, present=bool(rows)),
        max_rel_error=max(relative_values, default=0.0),
        min_coverage=min((row.coverage for row in rows), default=0.0),
    )
