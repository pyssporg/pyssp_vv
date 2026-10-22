"""Judgment: fabricated metric tables, no simulation, no numeric library."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyssp_vv.judge import Verdict, judge
from pyssp_vv.policy import (
    ComparisonPolicy,
    Criterion,
    MetricName,
    Policy,
    Sufficiency,
)


@dataclass(frozen=True)
class FakeMetric:
    signal: str = "h"
    coverage: float = 1.0
    max_abs_error: float = 0.0
    mean_abs_error: float = 0.0
    rmse: float = 0.0
    normalised_max_abs_error: float = 0.0
    reference_min: float = 0.0
    reference_max: float = 1.0
    shift_samples: int = 0
    undefined: tuple[str, ...] = ()


def policy(
    *,
    atol: float = 0.1,
    rtol: float = 0.0,
    metric: MetricName = MetricName.MAX_ABS,
    min_coverage: float = 0.0,
    degenerate_range: float = 0.0,
    shift_samples: int = 0,
    reject_boundary: bool = True,
) -> Policy:
    return Policy(
        comparison=ComparisonPolicy(shift_samples=shift_samples),
        criterion=Criterion(atol=atol, rtol=rtol, metric=metric),
        sufficiency=Sufficiency(
            min_coverage=min_coverage,
            degenerate_range=degenerate_range,
            reject_shift_at_boundary=reject_boundary,
        ),
    )


def codes(result) -> set[str]:
    return {reason.code for reason in result.reasons}


def test_within_tolerance_passes():
    result = judge([FakeMetric(max_abs_error=0.05)], policy(atol=0.1))
    assert result.verdict is Verdict.PASS
    assert result.signals[0].value == pytest.approx(0.05)


def test_exceeding_tolerance_fails_with_reason():
    result = judge([FakeMetric(max_abs_error=0.5)], policy(atol=0.1))
    assert result.verdict is Verdict.FAIL
    assert "criterion-exceeded" in codes(result)
    assert result.signals[0].limit == pytest.approx(0.1)


def test_rtol_scales_by_reference_peak():
    metric = FakeMetric(max_abs_error=1.0, reference_min=0.0, reference_max=100.0)
    assert judge([metric], policy(atol=0.0, rtol=0.01)).verdict is Verdict.PASS
    assert judge([metric], policy(atol=0.0, rtol=0.005)).verdict is Verdict.FAIL


def test_low_coverage_is_invalid_even_when_the_error_is_zero():
    result = judge([FakeMetric(max_abs_error=0.0, coverage=0.5)], policy(min_coverage=0.9))
    assert result.verdict is Verdict.INVALID
    assert "coverage-below-minimum" in codes(result)


def test_degenerate_reference_is_invalid():
    metric = FakeMetric(reference_min=0.0, reference_max=0.0)
    result = judge([metric], policy(degenerate_range=0.0))
    assert result.verdict is Verdict.INVALID
    assert "degenerate-signal" in codes(result)


def test_shift_at_the_search_boundary_is_invalid():
    metric = FakeMetric(max_abs_error=0.0, shift_samples=-3)
    result = judge([metric], policy(shift_samples=3))
    assert result.verdict is Verdict.INVALID
    assert "shift-at-boundary" in codes(result)


def test_shift_inside_the_window_is_judged_normally():
    metric = FakeMetric(max_abs_error=0.0, shift_samples=-1)
    result = judge([metric], policy(shift_samples=3))
    assert result.verdict is Verdict.PASS


def test_boundary_rejection_can_be_disabled():
    metric = FakeMetric(max_abs_error=0.0, shift_samples=3)
    result = judge([metric], policy(shift_samples=3, reject_boundary=False))
    assert result.verdict is Verdict.PASS


def test_non_finite_metric_is_invalid():
    result = judge([FakeMetric(max_abs_error=float("nan"))], policy())
    assert result.verdict is Verdict.INVALID
    assert "non-finite-metric" in codes(result)


def test_no_comparable_samples_is_invalid():
    result = judge([FakeMetric(undefined=("no-comparable-samples",))], policy())
    assert result.verdict is Verdict.INVALID
    assert "no-comparable-samples" in codes(result)


def test_normalised_metric_is_selectable():
    metric = FakeMetric(max_abs_error=10.0, normalised_max_abs_error=0.01)
    normalised = judge([metric], policy(atol=0.02, metric=MetricName.NORMALISED_MAX_ABS))
    absolute = judge([metric], policy(atol=0.02, metric=MetricName.MAX_ABS))
    assert normalised.verdict is Verdict.PASS
    assert absolute.verdict is Verdict.FAIL


def test_aggregation_is_pessimistic():
    good = FakeMetric(signal="good", max_abs_error=0.0)
    bad = FakeMetric(signal="bad", max_abs_error=1.0)
    result = judge([good, bad], policy(atol=0.1))
    assert result.verdict is Verdict.FAIL
    assert {item.signal: item.verdict for item in result.signals}["good"] is Verdict.PASS


def test_invalid_dominates_failure():
    bad = FakeMetric(signal="bad", max_abs_error=1.0)
    unfair = FakeMetric(signal="unfair", coverage=0.1)
    result = judge([bad, unfair], policy(atol=0.1, min_coverage=0.9))
    assert result.verdict is Verdict.INVALID


def test_no_metrics_is_invalid():
    result = judge([], policy())
    assert result.verdict is Verdict.INVALID
    assert "no-signals" in codes(result)
