#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import ConsolidationFunction, TimeRange, TimeSeries
from cmk.graphing_engine._resample import resample


def _ts(time_range: TimeRange, *values: float | None) -> TimeSeries:
    return TimeSeries(time_range=time_range, values=list(values))


def test_resample_keeps_a_matching_grid_unchanged() -> None:
    time_range = TimeRange(start=0, end=30, step=10)
    series = _ts(time_range, 1.0, 2.0, 3.0)
    assert resample(series, time_range, ConsolidationFunction.MAX) is series


def test_downsample_consolidates_buckets_with_the_consolidation_function() -> None:
    # Source has six 10s points; target halves the resolution to three 20s points.
    source = _ts(TimeRange(start=0, end=60, step=10), 1.0, 3.0, 5.0, 2.0, 9.0, 4.0)
    target = TimeRange(start=0, end=60, step=20)
    assert resample(source, target, ConsolidationFunction.MAX).values == [3.0, 5.0, 9.0]
    assert resample(source, target, ConsolidationFunction.MIN).values == [1.0, 2.0, 4.0]


def test_downsample_average_ignores_gaps() -> None:
    source = _ts(TimeRange(start=0, end=40, step=10), 2.0, None, 6.0, None)
    target = TimeRange(start=0, end=40, step=20)
    assert resample(source, target, ConsolidationFunction.AVERAGE).values == [2.0, 6.0]


def test_downsample_bucket_with_only_gaps_is_none() -> None:
    source = _ts(TimeRange(start=0, end=40, step=10), None, None, 5.0, 7.0)
    target = TimeRange(start=0, end=40, step=20)
    assert resample(source, target, ConsolidationFunction.MAX).values == [None, 7.0]


def test_forward_fill_upsamples_by_repeating_values() -> None:
    # Source has two 20s points; target doubles the resolution to four 10s points.
    source = _ts(TimeRange(start=0, end=40, step=20), 1.0, 2.0)
    target = TimeRange(start=0, end=40, step=10)
    assert resample(source, target, ConsolidationFunction.MAX).values == [1.0, 1.0, 2.0, 2.0]


def test_resample_of_an_empty_series_yields_the_target_length_of_gaps() -> None:
    source = _ts(TimeRange(start=0, end=30, step=10))
    target = TimeRange(start=0, end=30, step=10)
    # A matching grid short-circuits, so use a different one to exercise the empty path.
    other = TimeRange(start=0, end=30, step=15)
    assert resample(source, other, ConsolidationFunction.MAX).values == [None, None]
    assert resample(source, target, ConsolidationFunction.MAX) is source
