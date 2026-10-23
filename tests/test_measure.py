"""Measurement: the numeric expectations inherited from the upstream port."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pyssp_vv.measure import (
    Alignment,
    Grid,
    Trajectory,
    compare,
    compare_many,
    local_shift_error,
    local_shift_errors,
    metric_rows,
    resample,
)
from pyssp_vv.measure.alignment import Extrapolation, Interpolation


def traj(label: str, time, **channels) -> Trajectory:
    return Trajectory(
        time=np.asarray(time, dtype=float),
        channels={name: np.asarray(values, dtype=float) for name, values in channels.items()},
        label=label,
    )


class TestResample:
    def test_identity_grid(self):
        values = resample(np.array([0.0, 1.0]), np.array([5.0, 7.0]), np.array([0.0, 1.0]))
        np.testing.assert_allclose(values, [5.0, 7.0])

    def test_linear_interpolation(self):
        values = resample(np.array([0.0, 1.0]), np.array([0.0, 10.0]), np.array([0.25]))
        assert values[0] == pytest.approx(2.5)

    def test_out_of_range_clamps(self):
        values = resample(np.array([0.0, 1.0]), np.array([1.0, 2.0]), np.array([-1.0, 2.0]))
        np.testing.assert_allclose(values, [1.0, 2.0])

    def test_nan_samples_are_dropped(self):
        times = np.array([0.0, 0.5, 1.0])
        values = np.array([0.0, np.nan, 10.0])
        assert resample(times, values, np.array([0.5]))[0] == pytest.approx(5.0)

    def test_single_sample_constant(self):
        values = resample(np.array([0.0]), np.array([3.0]), np.array([-1.0, 1.0]))
        np.testing.assert_allclose(values, [3.0, 3.0])

    def test_all_nan_gives_nan(self):
        assert np.isnan(resample(np.array([0.0]), np.array([np.nan]), np.array([0.0]))[0])

    def test_step_interpolation_holds_previous_value(self):
        values = resample(
            np.array([0.0, 1.0]),
            np.array([0.0, 10.0]),
            np.array([0.0, 0.5, 1.0]),
            interpolation=Interpolation.STEP,
        )
        np.testing.assert_allclose(values, [0.0, 0.0, 10.0])

    def test_step_with_nan_extrapolation(self):
        values = resample(
            np.array([0.0, 1.0]),
            np.array([0.0, 10.0]),
            np.array([-1.0, 0.5, 2.0]),
            interpolation=Interpolation.STEP,
            extrapolation=Extrapolation.NAN,
        )
        assert np.isnan(values[0]) and values[1] == 0.0 and np.isnan(values[2])


class TestCompare:
    def test_identical_trajectories(self):
        reference = traj("a", [0.0, 0.5, 1.0], h=[1.0, 0.8, 0.6])
        candidate = traj("b", [0.0, 0.5, 1.0], h=[1.0, 0.8, 0.6])
        item = compare(reference, candidate).signals[0]
        assert item.max_abs_error == 0.0
        assert item.coverage == pytest.approx(1.0)

    def test_constant_offset(self):
        report = compare(traj("a", [0.0, 1.0], h=[1.0, 1.0]), traj("b", [0.0, 1.0], h=[1.5, 1.5]))
        item = report.signals[0]
        assert item.max_abs_error == pytest.approx(0.5)
        assert item.mean_abs_error == pytest.approx(0.5)
        assert item.rmse == pytest.approx(0.5)

    def test_different_time_grids_are_resampled(self):
        report = compare(
            traj("a", [0.0, 1.0, 2.0], h=[0.0, 10.0, 20.0]),
            traj("b", [0.0, 2.0], h=[1.0, 21.0]),
        )
        assert report.signals[0].max_abs_error == pytest.approx(1.0)

    def test_signal_subset(self):
        report = compare(
            traj("a", [0.0, 1.0], h=[1.0, 2.0], v=[0.0, 1.0]),
            traj("b", [0.0, 1.0], h=[1.0, 3.0], v=[0.0, 1.0]),
            signals=["v"],
        )
        assert [item.signal for item in report.signals] == ["v"]
        assert report.signals[0].max_abs_error == 0.0

    def test_missing_signal_raises(self):
        reference = traj("a", [0.0, 1.0], h=[1.0, 2.0])
        with pytest.raises(KeyError, match="missing from one of the trajectories"):
            compare(reference, reference, signals=["nope"])

    def test_disjoint_channels_use_common_only(self):
        report = compare(
            traj("a", [0.0, 1.0], h=[1.0, 2.0], v=[0.0, 0.0]),
            traj("b", [0.0, 1.0], h=[1.0, 2.0]),
        )
        assert [item.signal for item in report.signals] == ["h"]

    def test_no_common_signal_raises(self):
        with pytest.raises(ValueError, match="No signals selected"):
            compare(traj("a", [0.0], h=[1.0]), traj("b", [0.0], v=[1.0]))

    def test_explicit_grid_is_used_for_both_sides(self):
        window = Grid(start_time=0.0, stop_time=1.0, step_size=0.25)
        report = compare(
            traj("a", [0.0, 1.0], h=[0.0, 10.0]),
            traj("b", [0.0, 1.0], h=[0.0, 10.0]),
            alignment=Alignment(grid=window),
        )
        assert report.signals[0].max_abs_error == pytest.approx(0.0)
        assert window.time_grid().tolist() == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])
        assert report.alignment["grid"]["step_size"] == 0.25

    def test_invalid_grid_rejected(self):
        with pytest.raises(ValueError, match="stop_time"):
            Grid(start_time=1.0, stop_time=0.0, step_size=0.1)
        with pytest.raises(ValueError, match="step_size"):
            Grid(start_time=0.0, stop_time=1.0, step_size=0.0)

    def test_coverage_counts_comparable_samples(self):
        reference = traj("a", [0.0, 1.0, 2.0, 3.0], h=[0.0, 1.0, 2.0, 3.0])
        candidate = traj("b", [0.0, 1.0, 2.0, 3.0], h=[np.nan, 1.0, np.nan, 3.0])
        item = compare(reference, candidate).signals[0]
        assert item.coverage == pytest.approx(0.5)
        assert item.max_abs_error == pytest.approx(0.0)

    def test_shift_search_finds_the_lag(self):
        reference = traj("a", [0.0, 1.0, 2.0, 3.0], h=[0.0, 0.0, 10.0, 10.0])
        candidate = traj("b", [0.0, 1.0, 2.0, 3.0], h=[0.0, 0.0, 0.0, 10.0])
        item = compare(reference, candidate, alignment=Alignment(shift_samples=3)).signals[0]
        assert item.shift_samples == -1
        assert item.shift_max_abs_error == pytest.approx(0.0)
        assert item.max_abs_error == pytest.approx(10.0)

    def test_shift_is_not_searched_without_a_window(self):
        reference = traj("a", [0.0, 1.0], h=[0.0, 1.0])
        candidate = traj("b", [0.0, 1.0], h=[0.0, 2.0])
        item = compare(reference, candidate).signals[0]
        assert item.shift_samples == 0
        assert item.shift_max_abs_error == item.max_abs_error

    def test_local_shift_tolerates_per_sample_lag(self):
        reference = traj(
            "a", [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            h=[0.0, 0.0, 10.0, 10.0, 10.0, 10.0, 0.0, 0.0],
        )
        candidate = traj(
            "b", [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            h=[0.0, 0.0, 0.0, 10.0, 10.0, 0.0, 0.0, 0.0],
        )
        item = compare(
            reference,
            candidate,
            alignment=Alignment(shift_samples=3),
        ).signals[0]
        assert item.shift_max_abs_error == pytest.approx(10.0)
        local = local_shift_error(
            reference["h"],
            candidate["h"],
            max_shift=3,
        )
        assert np.nanmax(local) == pytest.approx(0.0)


class TestNormalisation:
    def test_reference_peak_denominator(self):
        item = compare(
            traj("a", [0.0, 1.0], h=[100.0, 100.0]),
            traj("b", [0.0, 1.0], h=[100.0, 100.5]),
        ).signals[0]
        assert item.denominator == pytest.approx(100.0)
        assert item.normalised_max_abs_error == pytest.approx(0.005)

    def test_unit_denominator(self):
        item = compare(
            traj("a", [0.0, 1.0], h=[100.0, 100.0]),
            traj("b", [0.0, 1.0], h=[100.0, 100.5]),
            normalisation="unit",
        ).signals[0]
        assert item.denominator == 1.0
        assert item.normalised_max_abs_error == pytest.approx(0.5)

    def test_zero_denominator_is_reported(self):
        item = compare(
            traj("a", [0.0, 1.0], h=[0.0, 0.0]),
            traj("b", [0.0, 1.0], h=[0.0, 0.0]),
            normalisation="reference_range",
        ).signals[0]
        assert item.denominator == 0.0
        assert item.normalised_max_abs_error == float("inf")
        assert "zero-denominator" in item.undefined

    def test_unknown_normalisation_rejected(self):
        with pytest.raises(ValueError, match="Unknown normalisation"):
            compare(traj("a", [0.0], h=[1.0]), traj("a", [0.0], h=[1.0]), normalisation="nope")


class TestComparisonTable:
    def test_rows_and_csv(self, tmp_path: Path):
        report = compare(
            traj("ref", [0.0, 1.0], h=[1.0, 1.0]),
            traj("cand", [0.0, 1.0], h=[1.0, 1.2]),
        )
        path = report.write_csv(tmp_path / "metrics.csv")
        lines = path.read_text().splitlines()
        assert lines[0].startswith("reference_label,candidate_label,signal")
        assert "cand" in lines[1]
        assert report.rows()[0]["coverage"] == pytest.approx(1.0)

    def test_compare_many_needs_two(self):
        with pytest.raises(ValueError, match="at least two"):
            compare_many([traj("a", [0.0], h=[1.0])])

    def test_compare_many_uses_first_as_reference(self):
        reference = traj("ref", [0.0, 1.0], h=[1.0, 1.0])
        close = traj("close", [0.0, 1.0], h=[1.0, 1.05])
        far = traj("far", [0.0, 1.0], h=[1.0, 2.0])
        pairs = compare_many([reference, close, far])
        assert [pair.candidate_label for pair in pairs] == ["close", "far"]
        assert pairs[0].signals[0].max_abs_error == pytest.approx(0.05)
        assert pairs[1].signals[0].max_abs_error == pytest.approx(1.0)

    def test_time_must_be_non_decreasing(self):
        with pytest.raises(ValueError, match="non-decreasing"):
            traj("a", [0.0, 1.0, 0.5], h=[0.0, 1.0, 2.0])

    def test_channel_length_mismatch_rejected(self):
        with pytest.raises(ValueError, match="samples"):
            traj("a", [0.0, 1.0], h=[0.0])


class TestLocalShiftErrors:
    def test_identical_series_are_zero(self):
        reference = traj("a", [0.0, 1.0, 2.0], h=[0.0, 1.0, 2.0])
        candidate = traj("b", [0.0, 1.0, 2.0], h=[0.0, 1.0, 2.0])
        errors = local_shift_errors(reference, candidate, alignment=Alignment(shift_samples=1))
        assert errors["h"] == pytest.approx(0.0)

    def test_one_sample_lag_is_tolerated(self):
        reference = traj("a", [0.0, 1.0, 2.0, 3.0], h=[0.0, 0.0, 10.0, 10.0])
        candidate = traj("b", [0.0, 1.0, 2.0, 3.0], h=[0.0, 10.0, 10.0, 10.0])
        errors = local_shift_errors(reference, candidate, alignment=Alignment(shift_samples=1))
        assert errors["h"] == pytest.approx(0.0)

    def test_without_a_shift_window_it_is_the_abs_error(self):
        reference = traj("a", [0.0, 1.0, 2.0, 3.0], h=[0.0, 0.0, 10.0, 10.0])
        candidate = traj("b", [0.0, 1.0, 2.0, 3.0], h=[0.0, 10.0, 10.0, 10.0])
        assert local_shift_errors(reference, candidate)["h"] == pytest.approx(10.0)

    def test_edge_samples_mask_the_tails_only_when_long_enough(self):
        reference = traj("a", [0.0, 1.0, 2.0, 3.0, 4.0], h=[5.0, 0.0, 0.0, 0.0, 5.0])
        candidate = traj("b", [0.0, 1.0, 2.0, 3.0, 4.0], h=[0.0, 0.0, 0.0, 0.0, 0.0])
        assert local_shift_errors(reference, candidate)["h"] == pytest.approx(5.0)
        assert local_shift_errors(reference, candidate, edge_samples=2)["h"] == pytest.approx(0.0)

        short_reference = traj("a", [0.0, 1.0, 2.0, 3.0], h=[5.0, 0.0, 0.0, 5.0])
        short_candidate = traj("b", [0.0, 1.0, 2.0, 3.0], h=[0.0, 0.0, 0.0, 0.0])
        assert local_shift_errors(
            short_reference, short_candidate, edge_samples=2
        )["h"] == pytest.approx(5.0)

    def test_keys_are_the_shared_channels(self):
        reference = traj("a", [0.0, 1.0], h=[0.0, 1.0], v=[0.0, 1.0])
        candidate = traj("b", [0.0, 1.0], h=[0.0, 1.0], w=[0.0, 1.0])
        assert set(local_shift_errors(reference, candidate)) == {"h"}

    def test_matches_local_shift_error_on_the_alignment_grid(self):
        alignment = Alignment(shift_samples=2)
        reference = traj(
            "a",
            [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            h=[0.0, 0.0, 10.0, 10.0, 10.0, 10.0, 0.0, 0.0],
        )
        candidate = traj(
            "b",
            [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            h=[0.0, 0.0, 0.0, 10.0, 10.0, 0.0, 0.0, 0.0],
        )
        target = alignment.target(reference.time)
        local = local_shift_error(
            resample(reference.time, reference["h"], target),
            resample(candidate.time, candidate["h"], target),
            max_shift=alignment.shift_samples,
        )
        expected = float(np.nanmax(local))
        assert local_shift_errors(
            reference, candidate, alignment=alignment
        )["h"] == pytest.approx(expected)

    def test_negative_edge_samples_raise(self):
        reference = traj("a", [0.0], h=[0.0])
        with pytest.raises(ValueError, match="non-negative"):
            local_shift_errors(reference, reference, edge_samples=-1)


class TestMetricRows:
    def test_maps_a_comparison_to_the_row_schema(self):
        report = compare(
            traj("ref", [0.0, 1.0], h=[1.0, 1.0]),
            traj("cand", [0.0, 1.0], h=[1.0, 1.2]),
        )
        row = metric_rows(report)[0]
        assert row.signal == "h"
        assert row.run_a_label == "ref"
        assert row.run_b_label == "cand"
        assert row.run_a_min == pytest.approx(1.0)
        assert row.run_a_max == pytest.approx(1.0)
        assert row.run_b_max == pytest.approx(1.2)
        assert row.max_abs_error == pytest.approx(0.2)
        assert row.max_shift_abs_error == pytest.approx(0.2)
        assert row.coverage == pytest.approx(1.0)
        assert row.shift_samples == 0
        assert row.normalisation == "reference_peak"
        assert row.denominator == pytest.approx(1.0)

    def test_max_shift_abs_error_overrides_per_signal(self):
        report = compare(
            traj("ref", [0.0, 1.0], h=[1.0, 1.0], v=[1.0, 1.0]),
            traj("cand", [0.0, 1.0], h=[1.2, 1.2], v=[1.5, 1.5]),
        )
        rows = {row.signal: row for row in metric_rows(report, max_shift_abs_error={"h": 0.01})}
        assert rows["h"].max_shift_abs_error == pytest.approx(0.01)
        assert rows["v"].max_shift_abs_error == pytest.approx(rows["v"].max_abs_error)
        assert rows["v"].max_abs_error == pytest.approx(0.5)

    def test_undefined_reasons_are_carried(self):
        report = compare(
            traj("a", [0.0, 1.0], h=[np.nan, np.nan]),
            traj("b", [0.0, 1.0], h=[0.0, 1.0]),
        )
        row = metric_rows(report)[0]
        assert "no-comparable-samples" in row.undefined
