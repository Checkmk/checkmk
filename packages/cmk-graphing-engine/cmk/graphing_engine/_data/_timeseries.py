#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class TimeRange:
    start: int
    end: int
    step: int


@dataclass(frozen=True, kw_only=True)
class TimeSeries:
    time_range: TimeRange
    values: Sequence[float | None]


def point_count(time_range: TimeRange) -> int:
    if time_range.step <= 0:
        return 0
    return max(0, (time_range.end - time_range.start) // time_range.step)


def timestamps(time_range: TimeRange) -> Sequence[int]:
    return [
        time_range.start + (index + 1) * time_range.step for index in range(point_count(time_range))
    ]


def fitted(time_series: TimeSeries, time_range: TimeRange) -> TimeSeries:
    num_points = point_count(time_range)
    values = list(time_series.values[:num_points])
    return TimeSeries(time_range=time_range, values=values + [None] * (num_points - len(values)))


def constant_time_series(value: float | None, time_range: TimeRange) -> TimeSeries:
    return TimeSeries(time_range=time_range, values=[value] * point_count(time_range))


def mapped_series(time_series: TimeSeries, transform: Callable[[float], float]) -> TimeSeries:
    return TimeSeries(
        time_range=time_series.time_range,
        values=[None if value is None else transform(value) for value in time_series.values],
    )


def scaled_series(time_series: TimeSeries, scale: float) -> TimeSeries:
    if scale == 1.0:
        return time_series
    return mapped_series(time_series, lambda value: value * scale)


def merge_series(time_series: Sequence[TimeSeries], time_range: TimeRange) -> TimeSeries:
    return TimeSeries(
        time_range=time_range,
        values=[
            next((value for value in point if value is not None), None)
            for point in zip(*(member.values for member in time_series))
        ],
    )


def last_present[T](values: Iterable[T | None]) -> T | None:
    last: T | None = None
    for value in values:
        if value is not None:
            last = value
    return last
