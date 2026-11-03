#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.graphing_engine import (
    constant_time_series,
    merge_series,
    scaled_series,
    TimeRange,
    TimeSeries,
    timestamps,
)


def test_each_point_sits_at_the_end_of_its_step() -> None:
    assert timestamps(TimeRange(start=0, end=180, step=60)) == [60, 120, 180]


def test_a_partial_last_step_holds_no_point() -> None:
    assert timestamps(TimeRange(start=0, end=150, step=60)) == [60, 120]


def test_a_range_without_a_step_holds_no_point() -> None:
    assert timestamps(TimeRange(start=0, end=180, step=0)) == []


def test_a_constant_series_has_one_value_per_point() -> None:
    time_range = TimeRange(start=0, end=150, step=60)

    assert len(constant_time_series(1.0, time_range).values) == len(timestamps(time_range))


def _series(start: int, end: int, step: int, values: Sequence[float | None]) -> TimeSeries:
    return TimeSeries(time_range=TimeRange(start=start, end=end, step=step), values=values)


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
