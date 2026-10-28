"""The measure -> judge seam.

``tests/test_judge.py`` judges ``FakeMetric``, a hand-built mirror of
``MetricView``. That proves the criterion logic and says nothing about the real
producer. These tests pin the seam itself: a renamed or dropped field in
``measure.metrics.SignalMetrics`` must fail here instead of passing quietly
against a fake that happens to be spelled the old way.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import get_type_hints

import numpy as np
import pytest

from pyssp_vv.evidence import (
    MetricRowView,
    as_metric_view,
    read_metric_csv,
    write_metric_csv,
)
from pyssp_vv.judge import judge, judge_signal
from pyssp_vv.judge.criteria import MetricView
from pyssp_vv.measure import Trajectory, compare, metric_rows
from pyssp_vv.measure.metrics import SignalMetrics
from pyssp_vv.policy import (
    ComparisonPolicy,
    Criterion,
    MetricName,
    Policy,
    Sufficiency,
)

#: Every attribute ``judge_signal`` reads from its metric argument
#: (judge.py:79-114), plus the value attributes selectable through
#: ``MetricName`` (policy/__init__.py:30-34). Kept explicit so that a new read
#: added to the judge without a matching protocol field is a visible edit here.
JUDGE_READS = (
    "signal",
    "coverage",
    "undefined",
    "reference_min",
    "reference_max",
    "shift_samples",
    "max_abs_error",
    "mean_abs_error",
    "rmse",
    "normalised_max_abs_error",
)


@dataclass(frozen=True)
class View:
    """``MetricView`` by hand: exactly the fields judgment is allowed to read."""

    signal: str
    coverage: float
    max_abs_error: float
    mean_abs_error: float
    rmse: float
    normalised_max_abs_error: float
    reference_min: float
    reference_max: float
    shift_samples: int
    undefined: tuple[str, ...] = ()


def comparison(*, candidate_values=(1.0, 2.5)):
    """A real comparison: reference ``h`` is ``[1.0, 2.0]`` on ``[0, 1]``."""
    reference = Trajectory(
        time=np.array([0.0, 1.0]),
        channels={"h": np.array([1.0, 2.0])},
        label="ref",
    )
    candidate = Trajectory(
        time=np.array([0.0, 1.0]),
        channels={"h": np.asarray(candidate_values, dtype=float)},
        label="cand",
    )
    return compare(reference, candidate)


def measurement(*, candidate_values=(1.0, 2.5)) -> SignalMetrics:
    """The measured signal of :func:`comparison`."""
    return comparison(candidate_values=candidate_values).signals[0]


def as_view(metric) -> View:
    """Copy a metric into the hand-built view, field for field."""
    return View(**{name: getattr(metric, name) for name in get_type_hints(View)})


def policy(
    *,
    atol: float = 0.1,
    metric: MetricName = MetricName.MAX_ABS,
    min_coverage: float = 0.0,
    degenerate_range: float = 0.0,
    shift_samples: int = 0,
) -> Policy:
    return Policy(
        comparison=ComparisonPolicy(shift_samples=shift_samples),
        criterion=Criterion(atol=atol, metric=metric),
        sufficiency=Sufficiency(
            min_coverage=min_coverage,
            degenerate_range=degenerate_range,
        ),
    )


def test_judge_reads_only_attributes_the_protocol_declares():
    declared = set(get_type_hints(MetricView))
    assert set(JUDGE_READS) <= declared, (
        "the judge reads an attribute MetricView does not declare: "
        f"{sorted(set(JUDGE_READS) - declared)}"
    )


def test_signal_metrics_declares_every_protocol_field_with_the_same_type():
    declared = get_type_hints(MetricView)
    produced = get_type_hints(SignalMetrics)

    missing = sorted(set(declared) - set(produced))
    assert not missing, (
        "SignalMetrics cannot feed judge_signal, it is missing MetricView fields: "
        f"{missing}"
    )

    mismatched = {
        name: (declared[name], produced[name])
        for name in declared
        if declared[name] != produced[name]
    }
    assert not mismatched, f"MetricView and SignalMetrics disagree on types: {mismatched}"


def test_a_real_measurement_satisfies_the_protocol_at_runtime():
    real = measurement()

    assert isinstance(real, MetricView)
    for name in get_type_hints(MetricView):
        assert hasattr(real, name), f"real measurement lacks {name!r}"

    # Shape, not just presence: a denominator accidentally left as a string
    # would satisfy hasattr and still break the comparison in judge_signal.
    assert isinstance(real.signal, str)
    assert isinstance(real.coverage, float)
    assert isinstance(real.max_abs_error, float)
    assert isinstance(real.mean_abs_error, float)
    assert isinstance(real.rmse, float)
    assert isinstance(real.normalised_max_abs_error, float)
    assert isinstance(real.reference_min, float)
    assert isinstance(real.reference_max, float)
    assert isinstance(real.shift_samples, int)
    assert isinstance(real.undefined, tuple)


def test_real_measurement_populates_the_numbers_the_judge_reads():
    real = measurement()

    # errors are |1-1| = 0 and |2-2.5| = 0.5:
    # mean = (0 + 0.5) / 2 = 0.25
    # rmse = sqrt((0^2 + 0.5^2) / 2) = sqrt(0.125)
    # reference peak = max(|1|, |2|) = 2, so normalised = 0.5 / 2 = 0.25
    assert real.signal == "h"
    assert real.coverage == pytest.approx(1.0)
    assert real.max_abs_error == pytest.approx(0.5)
    assert real.mean_abs_error == pytest.approx(0.25)
    assert real.rmse == pytest.approx(math.sqrt(0.125))
    assert real.reference_min == pytest.approx(1.0)
    assert real.reference_max == pytest.approx(2.0)
    assert real.normalised_max_abs_error == pytest.approx(0.25)
    assert real.shift_samples == 0
    assert real.undefined == ()


def test_judgment_from_real_metrics_equals_judgment_from_a_hand_built_view():
    real = measurement()
    view = as_view(real)
    assert isinstance(view, MetricView)

    policies = (
        policy(atol=0.6),  # pass
        policy(atol=0.4),  # criterion-exceeded
        policy(atol=0.3, metric=MetricName.RMSE),  # rmse 0.354 > 0.3
        policy(atol=0.2, metric=MetricName.NORMALISED_MAX_ABS),  # 0.25 > 0.2
        policy(atol=0.6, min_coverage=1.0),  # coverage is exactly 1.0
        policy(atol=0.6, degenerate_range=2.0),  # range 1.0 <= 2.0, invalid
    )

    for item in policies:
        real_judgment = judge([real], item)
        view_judgment = judge([view], item)
        assert real_judgment.to_dict() == view_judgment.to_dict()
        assert judge_signal(real, item).to_dict() == judge_signal(view, item).to_dict()
    assert {judge([real], item).verdict.value for item in policies} == {
        "pass",
        "fail",
        "invalid",
    }


def test_a_row_read_from_a_metrics_csv_can_be_judged(tmp_path):
    rows = metric_rows(comparison())
    path = write_metric_csv(tmp_path / "metrics.csv", rows)
    (row,) = read_metric_csv(path)

    view = as_metric_view(row)

    assert isinstance(view, MetricView)
    result = judge([view], policy(atol=0.6))
    assert result.verdict.value == "pass"
    assert result.signals[0].value == pytest.approx(0.5)


def test_the_adapter_declares_every_protocol_field_with_the_same_type():
    declared = get_type_hints(MetricView)
    produced = get_type_hints(MetricRowView)

    assert set(declared) <= set(produced), (
        "the CSV adapter cannot feed judge_signal: "
        f"{sorted(set(declared) - set(produced))}"
    )
    mismatched = {
        name: (declared[name], produced[name])
        for name in declared
        if declared[name] != produced[name]
    }
    assert not mismatched, f"MetricView and MetricRowView disagree on types: {mismatched}"


def test_adapter_and_signal_metrics_reach_the_same_verdict():
    # The same numbers, one from the durable row and one from the measurement
    # object. Every policy below either uses the reference range or the
    # reference peak, so a swapped run_a_min/run_a_max mapping changes a verdict.
    real = measurement()
    view = as_metric_view(metric_rows(comparison())[0])

    policies = (
        policy(atol=0.6),  # pass
        policy(atol=0.4),  # fail
        policy(atol=0.3, metric=MetricName.RMSE),  # fail
        policy(atol=0.2, metric=MetricName.NORMALISED_MAX_ABS),  # fail
        policy(atol=0.6, min_coverage=0.9),  # pass: coverage is 1.0
        policy(atol=0.6, degenerate_range=2.0),  # invalid: range 1.0 <= 2.0
    )

    for item in policies:
        assert judge([view], item).to_dict() == judge([real], item).to_dict()

    assert {judge([view], item).verdict.value for item in policies} == {
        "pass",
        "fail",
        "invalid",
    }


def test_sufficiency_paths_agree_between_real_metrics_and_the_view():
    gap = measurement(candidate_values=(np.nan, 2.5))  # coverage 0.5
    nothing = measurement(candidate_values=(np.nan, np.nan))  # nothing comparable

    cases = (
        (gap, policy(atol=1.0, min_coverage=0.9)),
        (nothing, policy(atol=1.0)),
    )

    for real, item in cases:
        view = as_view(real)
        assert judge([real], item).to_dict() == judge([view], item).to_dict()
        assert judge([real], item).verdict is judge([view], item).verdict
