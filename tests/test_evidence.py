"""Evidence bundles: hash-addressed, relative paths, JSON-only."""

from __future__ import annotations

import math

import pytest

from pyssp_vv.evidence import (
    METRIC_COLUMNS,
    ComparisonSummary,
    EvidenceBundle,
    InputRef,
    MetricRow,
    VerdictRecord,
    read_metric_csv,
    summarize_rows,
    write_metric_csv,
)
from pyssp_vv.evidence.hashing import digest_path
from pyssp_vv.judge import Verdict


def test_relative_path_and_digest(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = run_dir / "result.csv"
    result.write_text("time,y\n0,0\n1,1\n", encoding="utf-8")

    ref = InputRef.from_file("result", result, base_dir=run_dir)

    assert ref.path == "result.csv"
    assert ref.sha256.startswith("sha256:")
    assert ref.sha256 == digest_path(result)


def test_bundle_roundtrip(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = run_dir / "result.csv"
    result.write_text("time,y\n0,0\n", encoding="utf-8")

    bundle = EvidenceBundle(
        assessment_id="BouncingBall/baseline",
        inputs=(InputRef.from_file("result", result, base_dir=run_dir),),
        verdicts=(
            VerdictRecord(
                oracle_id="agreement",
                kind="cross_engine",
                verdict=Verdict.INVALID,
                metrics={"max_abs": 1.0},
                reasons=("coverage-below-minimum",),
            ),
        ),
        environment={"python": "3.10.12"},
        created="2026-10-22T00:00:00+00:00",
    )

    path = bundle.write(tmp_path / "out" / "evidence.json")

    assert path.is_absolute() and path.is_file()
    assert EvidenceBundle.read(path) == bundle


def test_directory_digest_tracks_content(tmp_path):
    tree = tmp_path / "ssp"
    (tree / "resources").mkdir(parents=True)
    (tree / "SystemStructure.ssd").write_text("<ssd/>", encoding="utf-8")
    before = digest_path(tree)

    (tree / "resources" / "model.fmu").write_bytes(b"fmu")
    assert digest_path(tree) != before


def test_non_json_metrics_fail_before_writing(tmp_path):
    bundle = EvidenceBundle(
        assessment_id="x/y",
        inputs=(),
        verdicts=(
            VerdictRecord(
                oracle_id="bad",
                kind="invariant",
                verdict=Verdict.FAIL,
                metrics={"value": object()},
            ),
        ),
        environment={},
        created="2026-10-22T00:00:00+00:00",
    )

    target = tmp_path / "evidence.json"
    with pytest.raises(TypeError):
        bundle.write(target)
    assert not target.exists()


def _row(**overrides) -> MetricRow:
    values: dict[str, object] = {
        "signal": "h",
        "max_abs_error": 0.5,
        "max_shift_abs_error": 0.25,
        "mean_abs_error": 0.2,
        "rmse": 0.3,
        "run_a_label": "reference",
        "run_a_min": 0.0,
        "run_a_max": 1.0,
        "run_b_label": "candidate",
        "run_b_min": 0.0,
        "run_b_max": 1.2,
        "coverage": 1.0,
        "shift_samples": 2,
        "normalisation": "reference_peak",
        "denominator": 1.0,
        "normalised_max_abs_error": 0.5,
    }
    values.update(overrides)
    return MetricRow(**values)


class TestMetricRow:
    def test_dict_follows_declared_columns_and_roundtrips(self):
        row = _row(undefined=("no-comparable-samples", "zero-denominator"))
        data = row.to_dict()
        assert tuple(data) == METRIC_COLUMNS
        assert data["undefined"] == "no-comparable-samples;zero-denominator"
        assert MetricRow.from_dict(data) == row

    def test_empty_undefined_roundtrips(self):
        row = _row()
        assert row.to_dict()["undefined"] == ""
        assert MetricRow.from_dict(row.to_dict()).undefined == ()


class TestMetricCsv:
    def test_roundtrip_including_nan_and_empty_undefined(self, tmp_path):
        rows = (
            _row(),
            _row(signal="v", undefined=("zero-denominator",)),
            _row(signal="w", max_abs_error=float("nan")),
        )
        path = write_metric_csv(tmp_path / "nested" / "metrics.csv", rows)
        assert path.is_file()
        assert path.read_text().splitlines()[0] == ",".join(METRIC_COLUMNS)

        read = read_metric_csv(path)
        assert read[0] == rows[0]
        assert read[1] == rows[1]
        assert read[2].signal == "w"
        assert math.isnan(read[2].max_abs_error)

    def test_read_rejects_a_missing_column(self, tmp_path):
        path = tmp_path / "metrics.csv"
        path.write_text("signal,max_abs_error\nh,0.1\n", encoding="utf-8")
        with pytest.raises(ValueError, match="missing columns"):
            read_metric_csv(path)


class TestSummary:
    def test_aggregates_rows(self):
        rows = [
            _row(
                signal="a",
                max_abs_error=1.0,
                max_shift_abs_error=0.5,
                mean_abs_error=0.2,
                rmse=0.3,
                normalised_max_abs_error=0.1,
                coverage=1.0,
            ),
            _row(
                signal="b",
                max_abs_error=2.0,
                max_shift_abs_error=0.25,
                mean_abs_error=0.4,
                rmse=0.5,
                normalised_max_abs_error=0.2,
                coverage=0.5,
            ),
        ]
        summary = summarize_rows(rows, time_points=11)
        assert summary.run_a_label == "reference"
        assert summary.run_b_label == "candidate"
        assert summary.time_points == 11
        assert summary.compared_signal_count == 2
        assert summary.max_abs_error == pytest.approx(2.0)
        assert summary.max_shift_abs_error == pytest.approx(0.5)
        assert summary.mean_abs_error == pytest.approx(0.3)
        assert summary.rmse == pytest.approx(0.4)
        assert summary.max_rel_error == pytest.approx(0.2)
        assert summary.min_coverage == pytest.approx(0.5)
        assert ComparisonSummary.from_dict(summary.to_dict()) == summary

    def test_non_finite_values_are_ignored_where_defined(self):
        rows = [
            _row(
                signal="a",
                mean_abs_error=float("nan"),
                rmse=0.5,
                normalised_max_abs_error=float("inf"),
                coverage=0.5,
            ),
            _row(
                signal="b",
                mean_abs_error=0.4,
                rmse=float("nan"),
                normalised_max_abs_error=0.25,
                coverage=1.0,
            ),
        ]
        summary = summarize_rows(rows, time_points=3)
        assert summary.mean_abs_error == pytest.approx(0.4)
        assert summary.rmse == pytest.approx(0.5)
        assert summary.max_rel_error == pytest.approx(0.25)
        assert summary.min_coverage == pytest.approx(0.5)

    def test_empty_rows_yield_zeros(self):
        summary = summarize_rows((), time_points=0)
        assert summary.run_a_label == ""
        assert summary.run_b_label == ""
        assert summary.time_points == 0
        assert summary.compared_signal_count == 0
        assert summary.max_abs_error == 0.0
        assert summary.max_shift_abs_error == 0.0
        assert summary.mean_abs_error == 0.0
        assert summary.rmse == 0.0
        assert summary.max_rel_error == 0.0
        assert summary.min_coverage == 0.0
