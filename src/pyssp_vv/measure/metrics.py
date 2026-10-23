"""Metric families and the comparison table.

Every metric carries the alignment and the denominator that produced it. A
number without those is not evidence: the same data yields different RMSE under
linear and step interpolation, and a normalised error without its denominator is
unreadable.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from pyssp_vv.evidence.metrics import MetricRow
from pyssp_vv.measure.alignment import (
    Alignment,
    best_shift,
    gap_blocks,
    local_shift_error,
    resample,
)
from pyssp_vv.measure.series import Trajectory

#: Strategies for the normalisation denominator.
DENOMINATORS = ("reference_peak", "reference_range", "unit")


@dataclass(frozen=True)
class SignalMetrics:
    """Measured difference for one channel.

    ``coverage`` is the fraction of target samples where both sides are finite.
    ``shift_*`` describe the best lag found inside the declared search window;
    they equal the unshifted metrics when no search was requested.
    """

    signal: str
    coverage: float
    max_abs_error: float
    mean_abs_error: float
    rmse: float
    reference_min: float
    reference_max: float
    candidate_min: float
    candidate_max: float
    shift_samples: int
    shift_max_abs_error: float
    normalisation: str
    denominator: float
    normalised_max_abs_error: float
    undefined: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "coverage": self.coverage,
            "max_abs_error": self.max_abs_error,
            "mean_abs_error": self.mean_abs_error,
            "rmse": self.rmse,
            "reference_min": self.reference_min,
            "reference_max": self.reference_max,
            "candidate_min": self.candidate_min,
            "candidate_max": self.candidate_max,
            "shift_samples": self.shift_samples,
            "shift_max_abs_error": self.shift_max_abs_error,
            "normalisation": self.normalisation,
            "denominator": self.denominator,
            "normalised_max_abs_error": self.normalised_max_abs_error,
        }


@dataclass(frozen=True)
class Comparison:
    """One reference/candidate pair, all selected signals."""

    reference_label: str
    candidate_label: str
    alignment: Mapping[str, Any]
    signals: tuple[SignalMetrics, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_label": self.reference_label,
            "candidate_label": self.candidate_label,
            "alignment": dict(self.alignment),
            "signals": [item.to_dict() for item in self.signals],
        }

    def rows(self) -> list[dict[str, Any]]:
        """Per-signal rows, ready for CSV or a table."""
        rows = []
        for item in self.signals:
            row = {"reference_label": self.reference_label, "candidate_label": self.candidate_label}
            row.update(item.to_dict())
            rows.append(row)
        return rows

    def write_csv(self, path: Path | str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = self.rows()
        fieldnames = list(rows[0]) if rows else ["signal"]
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return target


def _finite(values: np.ndarray) -> np.ndarray:
    return values[np.isfinite(values)]


def _denominator(name: str, reference: np.ndarray) -> float:
    if name == "unit":
        return 1.0
    finite = _finite(reference)
    if finite.size == 0:
        return float("nan")
    if name == "reference_peak":
        return float(max(abs(finite.min()), abs(finite.max())))
    if name == "reference_range":
        return float(finite.max() - finite.min())
    raise ValueError(f"Unknown normalisation {name!r}; expected one of {DENOMINATORS}")


def _compare_signal(
    name: str,
    reference: Trajectory,
    candidate: Trajectory,
    target: np.ndarray,
    alignment: Alignment,
    normalisation: str,
) -> SignalMetrics:
    ref_values = resample(
        reference.time,
        reference[name],
        target,
        interpolation=alignment.interpolation,
        extrapolation=alignment.extrapolation,
    )
    cand_values = resample(
        candidate.time,
        candidate[name],
        target,
        interpolation=alignment.interpolation,
        extrapolation=alignment.extrapolation,
    )

    paired = np.isfinite(ref_values) & np.isfinite(cand_values)
    blocked = gap_blocks(
        reference.time, reference[name], target, alignment.max_gap_samples
    ) | gap_blocks(candidate.time, candidate[name], target, alignment.max_gap_samples)
    paired &= ~blocked
    coverage = float(paired.sum() / target.size) if target.size else 0.0
    errors = np.abs(ref_values[paired] - cand_values[paired])

    undefined: list[str] = []
    if errors.size == 0:
        max_abs = mean_abs = rmse = float("nan")
        undefined.append("no-comparable-samples")
    else:
        max_abs = float(errors.max())
        mean_abs = float(errors.mean())
        rmse = float(np.sqrt(np.mean(np.square(errors))))

    ref_finite = _finite(ref_values)
    cand_finite = _finite(cand_values)
    reference_min = float(ref_finite.min()) if ref_finite.size else float("nan")
    reference_max = float(ref_finite.max()) if ref_finite.size else float("nan")
    candidate_min = float(cand_finite.min()) if cand_finite.size else float("nan")
    candidate_max = float(cand_finite.max()) if cand_finite.size else float("nan")

    if alignment.shift_samples > 0 and errors.size:
        shift_samples, shift_error = best_shift(
            ref_values, cand_values, max_shift=alignment.shift_samples
        )
    else:
        shift_samples, shift_error = 0, max_abs

    denominator = _denominator(normalisation, ref_values)
    if denominator > 0 and math.isfinite(denominator) and math.isfinite(max_abs):
        normalised = max_abs / denominator
    else:
        normalised = float("inf")
        undefined.append("zero-denominator")

    return SignalMetrics(
        signal=name,
        coverage=coverage,
        max_abs_error=max_abs,
        mean_abs_error=mean_abs,
        rmse=rmse,
        reference_min=reference_min,
        reference_max=reference_max,
        candidate_min=candidate_min,
        candidate_max=candidate_max,
        shift_samples=shift_samples,
        shift_max_abs_error=shift_error,
        normalisation=normalisation,
        denominator=denominator,
        normalised_max_abs_error=normalised,
        undefined=tuple(undefined),
    )


def compare(
    reference: Trajectory,
    candidate: Trajectory,
    *,
    signals: Sequence[str] | None = None,
    alignment: Alignment | None = None,
    normalisation: str = "reference_peak",
) -> Comparison:
    """Measure ``candidate`` against ``reference``.

    Signals default to the channels present on both sides. Asking for a channel
    that exists on only one side raises, rather than silently comparing nothing.
    """
    if normalisation not in DENOMINATORS:
        raise ValueError(f"Unknown normalisation {normalisation!r}; expected one of {DENOMINATORS}")
    alignment = alignment or Alignment()

    shared = tuple(sorted(set(reference.channels) & set(candidate.channels)))
    selected = tuple(signals) if signals is not None else shared
    missing = [name for name in selected if name not in shared]
    if missing:
        raise KeyError(f"Signals missing from one of the trajectories: {missing}")
    if not selected:
        raise ValueError("No signals selected for comparison")

    target = alignment.target(reference.time)
    metrics = tuple(
        _compare_signal(name, reference, candidate, target, alignment, normalisation)
        for name in selected
    )
    return Comparison(
        reference_label=reference.label,
        candidate_label=candidate.label,
        alignment={
            "interpolation": alignment.interpolation.value,
            "extrapolation": alignment.extrapolation.value,
            "shift_samples": alignment.shift_samples,
            "max_gap_samples": alignment.max_gap_samples,
            "grid": None
            if alignment.grid is None
            else {
                "start_time": alignment.grid.start_time,
                "stop_time": alignment.grid.stop_time,
                "step_size": alignment.grid.step_size,
            },
            "normalisation": normalisation,
        },
        signals=metrics,
    )


def compare_many(
    trajectories: Sequence[Trajectory],
    **kwargs: Any,
) -> tuple[Comparison, ...]:
    """Compare every trajectory against the first one, which acts as reference."""
    if len(trajectories) < 2:
        raise ValueError("Comparison needs at least two trajectories")
    reference = trajectories[0]
    return tuple(compare(reference, candidate, **kwargs) for candidate in trajectories[1:])


def local_shift_errors(
    reference: Trajectory,
    candidate: Trajectory,
    *,
    alignment: Alignment | None = None,
    edge_samples: int = 0,
) -> dict[str, float]:
    """Edge-masked per-sample minimum error over shifts, one entry per channel.

    The target grid is ``alignment.target(reference.time)`` and the shift window
    is ``alignment.shift_samples``. With ``edge_samples=N``, the first and last N
    comparable samples are treated as initialization/shutdown transients and
    excluded (only when the series is longer than ``2 * N``). Channels not
    present on both sides are skipped. Mirrors the semantics of
    :func:`local_shift_error` at the table level; it is not
    ``SignalMetrics.shift_max_abs_error``, which searches one lag for the whole
    series.
    """
    if edge_samples < 0:
        raise ValueError("edge_samples must be non-negative")
    alignment = alignment or Alignment()
    target = alignment.target(reference.time)
    shared = tuple(sorted(set(reference.channels) & set(candidate.channels)))

    errors: dict[str, float] = {}
    for name in shared:
        reference_values = resample(
            reference.time,
            reference[name],
            target,
            interpolation=alignment.interpolation,
            extrapolation=alignment.extrapolation,
        )
        candidate_values = resample(
            candidate.time,
            candidate[name],
            target,
            interpolation=alignment.interpolation,
            extrapolation=alignment.extrapolation,
        )
        error = local_shift_error(
            reference_values,
            candidate_values,
            max_shift=alignment.shift_samples,
        )
        if edge_samples and error.size > 2 * edge_samples:
            error[:edge_samples] = np.nan
            error[-edge_samples:] = np.nan
        finite = error[np.isfinite(error)]
        errors[name] = float(finite.max()) if finite.size else float("nan")
    return errors


def metric_rows(
    comparison: Comparison,
    *,
    max_shift_abs_error: Mapping[str, float] | None = None,
) -> tuple[MetricRow, ...]:
    """Map measured signals to the :mod:`pyssp_vv.evidence` row schema.

    ``max_shift_abs_error`` defaults to each signal's ``max_abs_error``. The
    row's ``run_a`` columns are the reference, ``run_b`` the candidate.
    """
    shifts = max_shift_abs_error or {}
    return tuple(
        MetricRow(
            signal=item.signal,
            max_abs_error=item.max_abs_error,
            max_shift_abs_error=float(shifts.get(item.signal, item.max_abs_error)),
            mean_abs_error=item.mean_abs_error,
            rmse=item.rmse,
            run_a_label=comparison.reference_label,
            run_a_min=item.reference_min,
            run_a_max=item.reference_max,
            run_b_label=comparison.candidate_label,
            run_b_min=item.candidate_min,
            run_b_max=item.candidate_max,
            coverage=item.coverage,
            shift_samples=item.shift_samples,
            normalisation=item.normalisation,
            denominator=item.denominator,
            normalised_max_abs_error=item.normalised_max_abs_error,
            undefined=item.undefined,
        )
        for item in comparison.signals
    )
