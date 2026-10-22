"""Measurement: how far apart two trajectories are.

Inputs are trajectories and numeric policy. Outputs are metrics. No verdict is
produced here; that is :mod:`pyssp_vv.judge`'s job.
"""

from pyssp_vv.measure.alignment import (
    Alignment,
    Grid,
    Interpolation,
    local_shift_error,
    resample,
)
from pyssp_vv.measure.metrics import Comparison, SignalMetrics, compare, compare_many
from pyssp_vv.measure.series import Trajectory

__all__ = [
    "Alignment",
    "Comparison",
    "Grid",
    "Interpolation",
    "SignalMetrics",
    "Trajectory",
    "compare",
    "compare_many",
    "local_shift_error",
    "resample",
]
