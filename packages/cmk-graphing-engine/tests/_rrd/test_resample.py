#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.graphing_engine import ConsolidationFunction, resample, TimeRange, TimeSeries


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


def test_a_finer_grid_has_as_many_points_as_its_timestamps() -> None:
    series = _series(0, 60, 30, [1.0, 2.0])
    resampled = resample(series, TimeRange(start=0, end=65, step=10), ConsolidationFunction.MAX)
    assert list(resampled.values) == [1.0, 1.0, 1.0, 2.0, 2.0, 2.0]


def test_a_shifted_finer_grid_reads_the_bucket_each_point_ends_in() -> None:
    series = _series(0, 60, 30, [1.0, 2.0])
    resampled = resample(series, TimeRange(start=5, end=55, step=10), ConsolidationFunction.MAX)
    assert list(resampled.values) == [1.0, 1.0, 2.0, 2.0, 2.0]


def test_an_empty_series_becomes_a_gap_on_the_requested_grid() -> None:
    resampled = resample(
        _series(0, 30, 10, []), TimeRange(start=0, end=60, step=20), ConsolidationFunction.MAX
    )
    assert list(resampled.values) == [None, None, None]
