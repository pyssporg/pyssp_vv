"""The trajectory container.

A trajectory is one time base and named channels. Per-channel time bases are not
modelled here: measurement channels sampled at different rates must be
resampled by the caller before comparison. That limitation is deliberate — it
keeps every alignment decision explicit.

Time must be non-decreasing. Duplicate timestamps are allowed and resolved at
resampling time (last sample wins for step holds, linear interpolation drops the
duplicate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class Trajectory:
    """One run or one reference series, addressed by channel name."""

    time: np.ndarray
    channels: Mapping[str, np.ndarray]
    label: str = ""
    units: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        time = np.asarray(self.time, dtype=np.float64)
        if time.ndim != 1:
            raise ValueError("time must be one-dimensional")
        if time.size and np.any(np.diff(time) < 0):
            raise ValueError("time must be non-decreasing")

        channels: dict[str, np.ndarray] = {}
        for name, values in self.channels.items():
            array = np.asarray(values, dtype=np.float64).reshape(-1)
            if array.shape != time.shape:
                raise ValueError(
                    f"channel {name!r} has {array.size} samples, time has {time.size}"
                )
            channels[name] = array

        unknown_units = set(self.units) - set(channels)
        if unknown_units:
            raise ValueError(f"units declared for unknown channels: {sorted(unknown_units)}")

        object.__setattr__(self, "time", time)
        object.__setattr__(self, "channels", channels)

    @property
    def signals(self) -> tuple[str, ...]:
        return tuple(sorted(self.channels))

    def __getitem__(self, name: str) -> np.ndarray:
        return self.channels[name]

    def __len__(self) -> int:
        return int(self.time.size)
