#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Sequence

from cmk.graphing_engine import (
    ConsolidationFunction,
    HostName,
    MetricName,
    RRDMetric,
    ServiceName,
    TimeRange,
    TimeSeries,
)
from cmk.gui.graphing._engine_series import (
    chop_last_empty_step,
    merge_series,
    resample,
    scaled_series,
)

_METRIC = RRDMetric(
    host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("x")
)


def _series(start: int, end: int, step: int, values: Sequence[float | None]) -> TimeSeries:
    return TimeSeries(time_range=TimeRange(start=start, end=end, step=step), values=values)


def test_a_series_already_on_the_grid_is_handed_back_unchanged() -> None:
    series = _series(0, 30, 10, [1.0, 2.0, 3.0])
    assert resample(series, series.time_range, ConsolidationFunction.MAX) is series


def test_a_coarser_grid_folds_each_bucket_with_the_consolidation_function() -> None:
    series = _series(0, 60, 10, [1.0, 5.0, 2.0, 6.0, 3.0, 7.0])
    coarse = TimeRange(start=0, end=60, step=30)
    assert list(resample(series, coarse, ConsolidationFunction.MAX).values) == [5.0, 7.0]
    assert list(resample(series, coarse, ConsolidationFunction.MIN).values) == [1.0, 3.0]
    assert list(resample(series, coarse, ConsolidationFunction.AVERAGE).values) == [
        8.0 / 3.0,
        16.0 / 3.0,
    ]


def test_a_bucket_without_a_single_value_folds_to_a_gap() -> None:
    series = _series(0, 60, 10, [1.0, 5.0, 2.0, None, None, None])
    resampled = resample(series, TimeRange(start=0, end=60, step=30), ConsolidationFunction.MAX)
    assert list(resampled.values) == [5.0, None]


def test_a_finer_grid_forward_fills_the_points_it_has() -> None:
    series = _series(0, 60, 30, [1.0, 2.0])
    resampled = resample(series, TimeRange(start=0, end=60, step=10), ConsolidationFunction.MAX)
    assert list(resampled.values) == [1.0, 1.0, 1.0, 2.0, 2.0, 2.0]


def test_an_empty_series_becomes_a_gap_on_the_requested_grid() -> None:
    resampled = resample(
        _series(0, 30, 10, []), TimeRange(start=0, end=60, step=20), ConsolidationFunction.MAX
    )
    assert list(resampled.values) == [None, None, None]


def test_scaling_multiplies_the_present_values_and_keeps_the_gaps() -> None:
    scaled = scaled_series(_series(0, 30, 10, [1.0, None, 3.0]), 1024)
    assert list(scaled.values) == [1024.0, None, 3072.0]


def test_scaling_by_one_hands_the_series_back_unchanged() -> None:
    series = _series(0, 30, 10, [1.0, 2.0, 3.0])
    assert scaled_series(series, 1.0) is series


def test_merging_takes_the_first_series_that_has_a_value_at_a_point() -> None:
    merged = merge_series(
        [_series(0, 30, 10, [None, 2.0, None]), _series(0, 30, 10, [9.0, 9.0, 9.0])],
        TimeRange(start=0, end=30, step=10),
    )
    assert list(merged.values) == [9.0, 2.0, 9.0]


def test_the_empty_trailing_step_of_a_graph_ending_now_is_dropped() -> None:
    # The current RRD step has no data yet, so an all-None last point is stripped rather than drawn as
    # a gap. "Now" is what makes it the current step, hence the clock.
    end = int(time.time())
    chopped = chop_last_empty_step({_METRIC: _series(end - 30, end, 10, [1.0, 2.0, None])}, end)
    assert list(chopped[_METRIC].values) == [1.0, 2.0]
    assert chopped[_METRIC].time_range == TimeRange(start=end - 30, end=end - 10, step=10)


def test_a_trailing_gap_in_the_past_is_kept() -> None:
    # Well before "now" an all-None last point is real missing data, not a step that has yet to fill.
    time_series = {_METRIC: _series(0, 30, 10, [1.0, 2.0, None])}
    assert chop_last_empty_step(time_series, 30) == time_series


def test_a_step_one_curve_still_has_data_for_is_kept() -> None:
    end = int(time.time())
    other = RRDMetric(
        host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("y")
    )
    time_series = {
        _METRIC: _series(end - 30, end, 10, [1.0, 2.0, None]),
        other: _series(end - 30, end, 10, [1.0, 2.0, 3.0]),
    }
    assert chop_last_empty_step(time_series, end) == time_series
