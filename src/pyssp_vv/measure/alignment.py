"""Alignment: choosing the grid and the interpolation that defines the error.

The interpolation policy changes the metric. Linear and step (`zero-order hold`)
give different RMSE on the same data, and step is the correct default for
discrete outputs while linear is correct for continuous states. Because of that,
alignment is explicit in every comparison and recorded in the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class Interpolation(str, Enum):
    LINEAR = "linear"
    STEP = "step"


class Extrapolation(str, Enum):
    CLAMP = "clamp"
    NAN = "nan"


@dataclass(frozen=True)
class Grid:
    """An explicit uniform time grid."""

    start_time: float
    stop_time: float
    step_size: float

    def __post_init__(self) -> None:
        if self.stop_time <= self.start_time:
            raise ValueError("stop_time must be greater than start_time")
        if self.step_size <= 0:
            raise ValueError("step_size must be positive")

    def time_grid(self) -> np.ndarray:
        span = self.stop_time - self.start_time
        steps = int(round(span / self.step_size))
        return np.linspace(self.start_time, self.stop_time, steps + 1, dtype=np.float64)


@dataclass(frozen=True)
class Alignment:
    """How two trajectories are put on a common grid.

    ``max_gap_samples`` is the number of consecutive invalid samples that may be
    interpolated across. ``0`` means a target that lands on an invalid sample, or
    strictly inside a gap, is not comparable. ``None`` interpolates across any
    gap — permissive, and recorded as such.
    """

    grid: Grid | None = None
    interpolation: Interpolation = Interpolation.LINEAR
    extrapolation: Extrapolation = Extrapolation.CLAMP
    shift_samples: int = 0
    max_gap_samples: int | None = 0

    def __post_init__(self) -> None:
        if self.shift_samples < 0:
            raise ValueError("shift_samples must be non-negative")
        if self.max_gap_samples is not None and self.max_gap_samples < 0:
            raise ValueError("max_gap_samples must be non-negative or None")

    def target(self, reference_time: np.ndarray) -> np.ndarray:
        return self.grid.time_grid() if self.grid is not None else np.asarray(reference_time)


def _last_true(valid: np.ndarray, index: np.ndarray) -> np.ndarray:
    """Index of the nearest True at or before each position (-1 if none)."""
    size = valid.size
    cumulative = np.maximum.accumulate(np.where(valid, np.arange(size), -1))
    safe = np.clip(index, 0, size - 1)
    return np.where(index >= 0, cumulative[safe], -1)


def _first_true(valid: np.ndarray, index: np.ndarray) -> np.ndarray:
    """Index of the nearest True at or after each position (size if none)."""
    size = valid.size
    reversed_running = np.minimum.accumulate(np.where(valid, np.arange(size), size)[::-1])[::-1]
    safe = np.clip(index, 0, size - 1)
    return np.where(index < size, reversed_running[safe], size)


def gap_blocks(
    times: np.ndarray,
    values: np.ndarray,
    target: np.ndarray,
    max_gap_samples: int | None,
) -> np.ndarray:
    """Mark target samples that a gap rule says are not comparable.

    A target is blocked when it coincides with an invalid sample, or when it
    falls strictly between two valid samples separated by more than
    ``max_gap_samples`` invalid ones. ``None`` blocks nothing.
    """
    times = np.asarray(times, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if max_gap_samples is None:
        return np.zeros(target.shape, dtype=bool)

    valid = np.isfinite(values) & np.isfinite(times)
    if valid.all():
        return np.zeros(target.shape, dtype=bool)

    size = times.size
    right = np.searchsorted(times, target, side="left")
    left = right - 1

    hit_right = (right < size) & (times[np.clip(right, 0, size - 1)] == target)
    hit_left = (left >= 0) & (times[np.clip(left, 0, size - 1)] == target)
    hit = hit_right | hit_left
    sample = np.where(hit_right, right, left)
    blocked = hit & ~valid[np.clip(sample, 0, size - 1)]

    left_valid = _last_true(valid, left)
    right_valid = _first_true(valid, right)
    inside = (left_valid >= 0) & (right_valid < size) & ~hit
    gap = np.where(inside, right_valid - left_valid - 1, 0)
    return blocked | (inside & (gap > max_gap_samples))


def resample(
    times: np.ndarray,
    values: np.ndarray,
    target: np.ndarray,
    *,
    interpolation: Interpolation = Interpolation.LINEAR,
    extrapolation: Extrapolation = Extrapolation.CLAMP,
) -> np.ndarray:
    """Resample ``values`` onto ``target`` times.

    Non-finite samples are dropped. A single valid sample becomes a constant
    series. Targets outside the source range are clamped or set to NaN according
    to ``extrapolation``.
    """
    times = np.asarray(times, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)

    valid = np.isfinite(times) & np.isfinite(values)
    valid_times = times[valid]
    valid_values = values[valid]
    if valid_times.size == 0:
        return np.full(target.shape, np.nan, dtype=np.float64)

    order = np.argsort(valid_times, kind="stable")
    valid_times = valid_times[order]
    valid_values = valid_values[order]
    unique_times, first = np.unique(valid_times, return_index=True)
    unique_values = valid_values[first]

    if unique_times.size == 1:
        return np.full(target.shape, float(unique_values[0]), dtype=np.float64)

    inside = (target >= unique_times[0]) & (target <= unique_times[-1])

    if interpolation is Interpolation.STEP:
        index = np.searchsorted(unique_times, target, side="right") - 1
        index = np.clip(index, 0, unique_times.size - 1)
        result = unique_values[index]
    elif interpolation is Interpolation.LINEAR:
        result = np.interp(
            target,
            unique_times,
            unique_values,
            left=float(unique_values[0]),
            right=float(unique_values[-1]),
        )
    else:  # pragma: no cover - enum exhaustiveness
        raise ValueError(f"Unknown interpolation: {interpolation}")

    if extrapolation is Extrapolation.NAN:
        result = np.where(inside, result, np.nan)
    return result.astype(np.float64, copy=False)


def shift_by(values: np.ndarray, samples: int) -> np.ndarray:
    """Delay (positive) or advance (negative) a series, filling with NaN."""
    values = np.asarray(values, dtype=np.float64)
    if samples == 0:
        return values.copy()
    result = np.full(values.shape, np.nan, dtype=np.float64)
    if samples > 0:
        if samples < values.size:
            result[samples:] = values[:-samples]
    else:
        offset = -samples
        if offset < values.size:
            result[: values.size - offset] = values[offset:]
    return result


def local_shift_error(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    max_shift: int,
) -> np.ndarray:
    """Per-sample minimum error over candidate shifts up to ``max_shift``.

    Unlike :func:`best_shift`, which chooses one lag for the whole series, this
    tolerates a lag that changes between samples, such as a discontinuity that
    reaches one component earlier than another.
    """
    reference = np.asarray(reference, dtype=np.float64)
    candidate = np.asarray(candidate, dtype=np.float64)
    error = np.abs(reference - candidate)
    for samples in range(1, max_shift + 1):
        if error.size <= samples:
            break
        error[samples:] = np.minimum(
            error[samples:], np.abs(reference[samples:] - candidate[:-samples])
        )
        error[:-samples] = np.minimum(
            error[:-samples], np.abs(reference[:-samples] - candidate[samples:])
        )
    return error


def best_shift(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    max_shift: int,
) -> tuple[int, float]:
    """Return the shift (in samples) that minimises the max absolute error.

    Ties are broken towards the smallest absolute shift. The error is computed
    only where both shifted series are finite. If no overlap has finite values,
    the shift is 0 and the error is NaN.
    """
    reference = np.asarray(reference, dtype=np.float64)
    candidate = np.asarray(candidate, dtype=np.float64)
    best = (0, float("nan"))
    best_key: tuple[float, float] | None = None

    for samples in range(-max_shift, max_shift + 1):
        shifted = shift_by(candidate, samples)
        with np.errstate(invalid="ignore"):
            errors = np.abs(reference - shifted)
        finite = errors[np.isfinite(errors)]
        if finite.size == 0:
            continue
        error = float(np.max(finite))
        key = (error, float(abs(samples)))
        if best_key is None or key < best_key:
            best_key = key
            best = (samples, error)
    return best
