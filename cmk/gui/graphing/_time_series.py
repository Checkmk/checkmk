#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Sequence
from statistics import fmean

Timestamp = int

TimeWindow = tuple[Timestamp, Timestamp, int]
TimeSeriesValue = float | None
TimeSeriesValues = Sequence[TimeSeriesValue]


def rrd_timestamps(time_window: TimeWindow) -> list[Timestamp]:
    start, end, step = time_window
    return [] if step == 0 else [t + step for t in range(start, end, step)]


def aggregation_functions(series: TimeSeriesValues, aggr: str | None) -> TimeSeriesValue:
    """Aggregate data in series list according to aggr

    If series has None values they are dropped before aggregation"""
    cleaned_series = [x for x in series if x is not None]
    if not cleaned_series:
        return None

    aggr = "max" if aggr is None else aggr.lower()
    match aggr:
        case "average":
            return fmean(cleaned_series)
        case "max":
            return max(cleaned_series)
        case "min":
            return min(cleaned_series)
        case _:
            raise ValueError(f"Invalid Aggregation function {aggr}, only max, min, average allowed")


class TimeSeries:
    """Describes the returned time series returned by livestatus

    - Timestamped values are valid for the measurement interval:
        [timestamp-step; timestamp[
      which means they are at the end of the interval.
    - The Series describes the interval [start; end[
    - Start has no associated value to it.

    args:
        data : list
            Includes [start, end, step, *values]
        timewindow: tuple
            describes (start, end, step), in this case data has only values
        conversion:
            optional conversion to account for user-specific unit settings

    """

    def __init__(
        self,
        data: TimeSeriesValues,
        time_window: TimeWindow,
        conversion: Callable[[float], float] = lambda v: v,
    ) -> None:
        self.start = int(time_window[0])
        self.end = int(time_window[1])
        self.step = int(time_window[2])
        self.values: TimeSeriesValues = [v if v is None else conversion(v) for v in data]

    @property
    def twindow(self) -> TimeWindow:
        return self.start, self.end, self.step

    def forward_fill_resample(self, twindow: TimeWindow) -> TimeSeriesValues:
        """Upsample by forward filling values

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        """
        if twindow == self.twindow:
            return self.values

        idx_max = len(self.values) - 1

        return [
            self.values[max(0, min(int((t - self.start) / self.step), idx_max))]
            for t in range(*twindow)
        ]

    def downsample(self, twindow: TimeWindow, cf: str | None = "max") -> TimeSeriesValues:
        """Downsample time series by consolidation function

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        cf : str ('max', 'average', 'min')
             consolidation function imitating RRD methods
        """
        if twindow == self.twindow:
            return self.values

        dwsa = []
        co: list[TimeSeriesValue] = []
        desired_times = rrd_timestamps(twindow)
        i = 0
        for t, val in self.time_data_pairs():
            if t > desired_times[i]:
                dwsa.append(aggregation_functions(co, cf))
                co = []
                i += 1
            co.append(val)

        diff_len = len(desired_times) - len(dwsa)
        if diff_len > 0:
            dwsa.append(aggregation_functions(co, cf))
            dwsa += [None] * (diff_len - 1)

        return dwsa

    def time_data_pairs(self) -> list[tuple[Timestamp, TimeSeriesValue]]:
        return list(zip(rrd_timestamps(self.twindow), self.values))

    def __repr__(self) -> str:
        return f"TimeSeries({self.values}, timewindow={self.twindow})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeSeries):
            return NotImplemented

        return (
            self.start == other.start
            and self.end == other.end
            and self.step == other.step
            and self.values == other.values
        )

    def __getitem__(self, i: int) -> TimeSeriesValue:
        return self.values[i]

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self) -> Iterator[TimeSeriesValue]:
        yield from self.values

    def count(self, /, v: TimeSeriesValue) -> int:
        return self.values.count(v)
