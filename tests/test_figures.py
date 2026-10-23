"""Figure specification and the matplotlib adapter.

The spec is plain data and must be constructible without matplotlib; only
:func:`render_figure` imports it.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest

from pyssp_vv.measure import Trajectory, build_figure_spec, render_figure


def traj(label: str, time, **channels) -> Trajectory:
    return Trajectory(
        time=np.asarray(time, dtype=float),
        channels={name: np.asarray(values, dtype=float) for name, values in channels.items()},
        label=label,
    )


def _png_dpi(path: Path) -> int:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    position = 8
    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        payload = data[position + 8 : position + 8 + length]
        if kind == b"pHYs":
            pixels_per_metre = struct.unpack(">I", payload[:4])[0]
            return round(pixels_per_metre * 0.0254)
        position += 12 + length
    raise AssertionError(f"PNG has no pHYs chunk: {path}")


class TestBuildFigureSpec:
    def test_defaults_to_the_signal_as_title(self):
        spec = build_figure_spec([traj("a", [0.0, 1.0], h=[0.0, 1.0])], signal="h")
        assert spec.title == "h"
        assert spec.x_label == "time"
        assert spec.y_label is None
        assert spec.tolerance is None

    def test_explicit_labels_are_kept(self):
        spec = build_figure_spec(
            [traj("a", [0.0, 1.0], h=[0.0, 1.0])],
            signal="h",
            title="model/case - h",
            tolerance=0.1,
            x_label="t",
            y_label="height",
        )
        assert spec.title == "model/case - h"
        assert spec.tolerance == 0.1
        assert spec.x_label == "t"
        assert spec.y_label == "height"

    def test_series_order_is_preserved(self):
        first = traj("a", [0.0, 1.0], h=[0.0, 1.0])
        second = traj("b", [0.0, 1.0], h=[0.0, 2.0])
        spec = build_figure_spec([first, second], signal="h")
        assert spec.series[0] is first
        assert spec.series[1] is second

    def test_empty_series_raises(self):
        with pytest.raises(ValueError, match="at least one series"):
            build_figure_spec([], signal="h")

    def test_missing_signal_raises(self):
        with pytest.raises(ValueError, match="missing from"):
            build_figure_spec(
                [traj("a", [0.0, 1.0], h=[0.0, 1.0]), traj("b", [0.0, 1.0], v=[0.0, 1.0])],
                signal="h",
            )

    def test_negative_tolerance_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            build_figure_spec([traj("a", [0.0, 1.0], h=[0.0, 1.0])], signal="h", tolerance=-0.1)


class TestRenderFigure:
    def test_writes_a_png_and_returns_an_absolute_path(self, tmp_path):
        pytest.importorskip("matplotlib")
        spec = build_figure_spec(
            [
                traj("reference", [0.0, 0.5, 1.0], h=[1.0, 0.8, 0.6]),
                traj("candidate", [0.0, 0.5, 1.0], h=[1.0, 0.75, 0.6]),
            ],
            signal="h",
        )
        target = tmp_path / "plots" / "figure.png"

        result = render_figure(spec, target)

        assert result == target.resolve()
        assert result.is_file()
        assert result.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.parametrize("dpi", [80, 160])
    def test_honours_dpi(self, tmp_path, dpi):
        pytest.importorskip("matplotlib")
        spec = build_figure_spec([traj("a", [0.0, 1.0], h=[0.0, 1.0])], signal="h")
        result = render_figure(spec, tmp_path / f"figure-{dpi}.png", dpi=dpi)
        assert _png_dpi(result) == pytest.approx(dpi, abs=1)

    def test_tolerance_draws_a_band(self, tmp_path):
        pytest.importorskip("matplotlib")
        series = [traj("reference", [0.0, 0.5, 1.0], h=[1.0, 0.8, 0.6])]

        plain = render_figure(
            build_figure_spec(series, signal="h"), tmp_path / "plain.png"
        )
        banded = render_figure(
            build_figure_spec(series, signal="h", tolerance=0.1),
            tmp_path / "banded.png",
        )

        assert plain.read_bytes() != banded.read_bytes()
