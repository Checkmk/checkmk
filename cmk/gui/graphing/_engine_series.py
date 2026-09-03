#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, Sequence
from statistics import fmean

from cmk.graphing_engine import (
    ConsolidationFunction,
    RRDMetric,
    TimeRange,
    TimeSeries,
)


def _timestamps(time_range: TimeRange) -> Sequence[int]:
    if time_range.step <= 0:
        return []
    return [t + time_range.step for t in range(time_range.start, time_range.end, time_range.step)]


def _aggregate(
    values: Sequence[float | None], consolidation_function: ConsolidationFunction
) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    match consolidation_function:
        case ConsolidationFunction.MIN:
            return min(present)
        case ConsolidationFunction.MAX:
            return max(present)
        case ConsolidationFunction.AVERAGE:
            return fmean(present)


def _downsample(
    time_series: TimeSeries,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> Sequence[float | None]:
    desired = _timestamps(time_range)
    resampled: list[float | None] = []
    bucket: list[float | None] = []
    index = 0
    for timestamp, value in zip(_timestamps(time_series.time_range), time_series.values):
        if index < len(desired) and timestamp > desired[index]:
            resampled.append(_aggregate(bucket, consolidation_function))
            bucket = []
            index += 1
        bucket.append(value)
    if (missing := len(desired) - len(resampled)) > 0:
        resampled.append(_aggregate(bucket, consolidation_function))
        resampled += [None] * (missing - 1)
    return resampled


def _forward_fill(time_series: TimeSeries, time_range: TimeRange) -> Sequence[float | None]:
    source = time_series.time_range
    last = len(time_series.values) - 1
    return [
        time_series.values[max(0, min((timestamp - source.start) // source.step, last))]
        for timestamp in range(time_range.start, time_range.end, time_range.step)
    ]


def resample(
    time_series: TimeSeries,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> TimeSeries:
    if time_series.time_range == time_range:
        return time_series
    if not time_series.values or time_series.time_range.step <= 0:
        return TimeSeries(time_range=time_range, values=[None] * len(_timestamps(time_range)))
    values = (
        _downsample(time_series, time_range, consolidation_function)
        if time_range.step >= time_series.time_range.step
        else _forward_fill(time_series, time_range)
    )
    return TimeSeries(time_range=time_range, values=values)


def scaled_series(time_series: TimeSeries, scale: float) -> TimeSeries:
    if scale == 1.0:
        return time_series
    return TimeSeries(
        time_range=time_series.time_range,
        values=[None if value is None else value * scale for value in time_series.values],
    )


def merge_series(time_series: Sequence[TimeSeries], time_range: TimeRange) -> TimeSeries:
    return TimeSeries(
        time_range=time_range,
        values=[
            next((value for value in point if value is not None), None)
            for point in zip(*(member.values for member in time_series))
        ],
    )


def chop_last_empty_step(
    time_series: Mapping[RRDMetric, TimeSeries], end: int
) -> Mapping[RRDMetric, TimeSeries]:
    # Drop the empty trailing step of a graph that ends "now": the current RRD step has no data yet,
    # so an all-None last point across every curve is stripped rather than drawn as a gap (matches
    # the legacy _chop_last_empty_step).
    if not time_series:
        return time_series
    step = next(iter(time_series.values())).time_range.step
    if step <= 0 or abs(time.time() - end) > step:
        return time_series
    if not all(series.values and series.values[-1] is None for series in time_series.values()):
        return time_series
    return {
        metric: TimeSeries(
            time_range=TimeRange(
                start=series.time_range.start, end=series.time_range.end - step, step=step
            ),
            values=series.values[:-1],
        )
        for metric, series in time_series.items()
    }
