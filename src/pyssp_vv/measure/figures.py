"""Figure specification: rendering as a view of a comparison.

A figure is described as data — what is overlaid, on which signal, with an
optional tolerance band — so a consumer can build or inspect it without
matplotlib. Rendering is a separate adapter: :func:`render_figure` imports
matplotlib inside the function and forces the Agg backend, so importing this
module stays matplotlib-free. Matplotlib is the ``figures`` extra, never a
module-level dependency of ``measure``.

Figures are derived artifacts: regenerable from the comparison and the policy,
never hashed into evidence, and never an acceptance criterion. A comparison
figure draws the criterion band, so a reader can see what was judged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pyssp_vv.measure.series import Trajectory

_LINE_STYLES = ("-", "--", ":", "-.")
_START_MARKERS = ("o", "s", "^", "D", "v", "P", "X")


@dataclass(frozen=True)
class FigureSpec:
    """What one comparison figure shows, as data.

    ``series`` are overlaid in order; ``series[0]`` is the reference when
    ``tolerance`` is given. ``tolerance`` draws a ± band around the reference
    so a reader can see what was judged. A figure is never an acceptance
    criterion and is never hashed into evidence.
    """

    title: str
    signal: str
    series: tuple[Trajectory, ...]
    tolerance: float | None = None
    x_label: str = "time"
    y_label: str | None = None

    def __post_init__(self) -> None:
        if not self.series:
            raise ValueError("A figure needs at least one series")
        missing = [
            series.label or f"series {index}"
            for index, series in enumerate(self.series)
            if self.signal not in series.channels
        ]
        if missing:
            raise ValueError(
                f"signal {self.signal!r} missing from: {', '.join(missing)}"
            )
        if self.tolerance is not None and self.tolerance < 0:
            raise ValueError("tolerance must be non-negative")


def build_figure_spec(
    series: Sequence[Trajectory],
    *,
    signal: str,
    title: str | None = None,
    tolerance: float | None = None,
    x_label: str = "time",
    y_label: str | None = None,
) -> FigureSpec:
    """Describe one figure, defaulting its title to the signal name."""
    return FigureSpec(
        title=signal if title is None else title,
        signal=signal,
        series=tuple(series),
        tolerance=tolerance,
        x_label=x_label,
        y_label=y_label,
    )


def _series_style(index: int) -> tuple[str, str]:
    return _LINE_STYLES[index % len(_LINE_STYLES)], _START_MARKERS[index % len(_START_MARKERS)]


def render_figure(
    spec: FigureSpec,
    path: Path | str,
    *,
    dpi: int = 160,
) -> Path:
    """Render one PNG and return its absolute path.

    matplotlib is imported inside this function and configured with the Agg
    backend, so importing pyssp_vv.measure.figures stays matplotlib-free.
    """
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(figsize=(14, 6))
    for index, series in enumerate(spec.series):
        line_style, start_marker = _series_style(index)
        axes.plot(
            series.time,
            series[spec.signal],
            label=series.label or f"series {index}",
            linewidth=1.4,
            linestyle=line_style,
            marker=start_marker,
            markevery=[0],
            markersize=7,
            markerfacecolor="white",
            markeredgewidth=1.3,
        )

    if spec.tolerance is not None:
        reference = spec.series[0]
        values = reference[spec.signal]
        axes.fill_between(
            reference.time,
            values - spec.tolerance,
            values + spec.tolerance,
            alpha=0.2,
            label=f"±{spec.tolerance:g}",
        )

    axes.set_title(spec.title)
    axes.set_xlabel(spec.x_label)
    axes.set_ylabel(spec.y_label or spec.signal)
    axes.grid(True, alpha=0.25)
    axes.legend(loc="best")
    figure.tight_layout()
    figure.savefig(target, dpi=dpi)
    plt.close(figure)
    return target.resolve()
