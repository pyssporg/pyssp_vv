"""The metric view a judgment consumes.

Judgment needs no numeric library: it reads attributes that the measurement
layer already produces. Anything structurally compatible works, which keeps the
contracts testable with fabricated tables.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MetricView(Protocol):
    signal: str
    coverage: float
    max_abs_error: float
    mean_abs_error: float
    rmse: float
    normalised_max_abs_error: float
    reference_min: float
    reference_max: float
    shift_samples: int
    undefined: tuple[str, ...]
