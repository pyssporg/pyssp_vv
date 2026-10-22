"""Policies are data: they round-trip and reject nonsense."""

from __future__ import annotations

import json

import pytest

from pyssp_vv.judge import Assessment, Factor, OracleRef
from pyssp_vv.policy import (
    ComparisonPolicy,
    Criterion,
    CriterionKind,
    MetricName,
    Policy,
    Sufficiency,
)


def make_policy() -> Policy:
    return Policy(
        comparison=ComparisonPolicy(interpolation="step", shift_samples=2, grid=(0.0, 1.0, 0.01)),
        criterion=Criterion(atol=1e-3, rtol=1e-2, kind=CriterionKind.EQUIVALENCE),
        sufficiency=Sufficiency(min_coverage=0.95, degenerate_range=1e-9),
    )


def test_policy_roundtrip_is_json_safe():
    original = make_policy()
    data = original.to_dict()
    assert json.loads(json.dumps(data)) == data
    assert Policy.from_dict(data) == original


def test_criterion_limit():
    criterion = Criterion(atol=0.1, rtol=0.1)
    assert criterion.limit(10.0) == pytest.approx(1.1)
    assert criterion.holds(1.0, 10.0)
    assert not criterion.holds(1.2, 10.0)


def test_negative_criterion_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        Criterion(atol=-1.0)


def test_sufficiency_range():
    with pytest.raises(ValueError, match="min_coverage"):
        Sufficiency(min_coverage=1.5)


def test_comparison_policy_validates():
    with pytest.raises(ValueError, match="interpolation"):
        ComparisonPolicy(interpolation="cubic")
    with pytest.raises(ValueError, match="grid"):
        ComparisonPolicy(grid=(1.0, 0.0, 0.1))


def test_metric_name_is_explicit():
    assert {item.value for item in MetricName} == {
        "max_abs_error",
        "mean_abs_error",
        "rmse",
        "normalised_max_abs_error",
    }


def make_assessment() -> Assessment:
    return Assessment(
        assessment_id="BouncingBall/baseline",
        model="BouncingBall",
        case="baseline",
        factor=Factor("engine", levels=("ssp4sim", "omsimulator")),
        held=("window", "step_size", "param_set"),
        oracles=(
            OracleRef(oracle_id="agreement", kind="cross_engine", policy=make_policy()),
        ),
    )


def test_assessment_roundtrip():
    original = make_assessment()
    data = original.to_dict()
    assert json.loads(json.dumps(data)) == data
    assert Assessment.from_dict(data) == original


def test_assessment_rejects_unknown_keys():
    data = make_assessment().to_dict()
    data["extra"] = 1
    with pytest.raises(ValueError, match="Unknown assessment keys"):
        Assessment.from_dict(data)


def test_factor_cannot_be_held():
    data = make_assessment().to_dict()
    data["held"] = ["engine"]
    with pytest.raises(ValueError, match="both the independent factor"):
        Assessment.from_dict(data)


def test_assessment_needs_an_oracle():
    data = make_assessment().to_dict()
    data["oracles"] = []
    with pytest.raises(ValueError, match="at least one oracle"):
        Assessment.from_dict(data)
