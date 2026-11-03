#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from statistics import fmean

from cmk.graphing_engine._data._timeseries import point_count, TimeRange, TimeSeries, timestamps

from ._metrics import ConsolidationFunction


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
    desired = timestamps(time_range)
    resampled: list[float | None] = []
    bucket: list[float | None] = []
    index = 0
    for timestamp, value in zip(timestamps(time_series.time_range), time_series.values):
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
        time_series.values[max(0, min((timestamp - source.start - 1) // source.step, last))]
        for timestamp in timestamps(time_range)
    ]


def resample(
    time_series: TimeSeries,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> TimeSeries:
    if time_series.time_range == time_range:
        return time_series
    if not time_series.values or time_series.time_range.step <= 0:
        return TimeSeries(time_range=time_range, values=[None] * point_count(time_range))
    values = (
        _downsample(time_series, time_range, consolidation_function)
        if time_range.step >= time_series.time_range.step
        else _forward_fill(time_series, time_range)
    )
    return TimeSeries(time_range=time_range, values=values)
