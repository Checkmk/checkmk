#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from statistics import fmean

from ._objects import TimeSeries
from ._options import ConsolidationFunction, TimeRange

# RRDTool serves each column on its own grid: it snaps start/end to step boundaries and returns
# whatever RRA resolution it has, so a fetched series' grid may differ from the one requested. The
# engine combines series point by point against a single grid, so every fetched series is aligned
# to the requested time range here before it is merged or evaluated.


def _timestamps(time_range: TimeRange) -> list[int]:
    # A value is valid for the interval (timestamp - step, timestamp], i.e. it sits at the end of
    # its step, so the first timestamp is start + step.
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
    series: TimeSeries,
    target: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> list[float | None]:
    """Reduce a finer series onto a coarser grid, consolidating each bucket of source points."""
    desired = _timestamps(target)
    resampled: list[float | None] = []
    bucket: list[float | None] = []
    index = 0
    for timestamp, value in zip(_timestamps(series.time_range), series.values):
        if index < len(desired) and timestamp > desired[index]:
            resampled.append(_aggregate(bucket, consolidation_function))
            bucket = []
            index += 1
        bucket.append(value)
    if (missing := len(desired) - len(resampled)) > 0:
        resampled.append(_aggregate(bucket, consolidation_function))
        resampled += [None] * (missing - 1)
    return resampled


def _forward_fill(series: TimeSeries, target: TimeRange) -> list[float | None]:
    """Spread a coarser series onto a finer grid by repeating the value covering each timestamp."""
    source = series.time_range
    last = len(series.values) - 1
    return [
        series.values[max(0, min((timestamp - source.start) // source.step, last))]
        for timestamp in range(target.start, target.end, target.step)
    ]


def resample(
    series: TimeSeries,
    target: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> TimeSeries:
    """Align a fetched series to the requested grid (down- or up-sampling as needed)."""
    if series.time_range == target:
        return series
    if not series.values or series.time_range.step <= 0:
        return TimeSeries(time_range=target, values=[None] * len(_timestamps(target)))
    values = (
        _downsample(series, target, consolidation_function)
        if target.step >= series.time_range.step
        else _forward_fill(series, target)
    )
    return TimeSeries(time_range=target, values=values)
