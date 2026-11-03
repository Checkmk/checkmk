#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Final, Protocol

from cmk.graphing_engine._data._naming import MetricName
from cmk.graphing_engine._data._timeseries import TimeRange, TimeSeries

from ._naming import Service


class FetchMetricNamesProtocol(Protocol):
    def __call__(self) -> Mapping[Service, frozenset[MetricName]]: ...


_COLUMN_HEADER_LENGTH: Final = 3


def time_series_of_rrd_column(column: Sequence[float | None]) -> TimeSeries | None:
    if len(column) <= _COLUMN_HEADER_LENGTH:
        return None
    start, end, step = column[:_COLUMN_HEADER_LENGTH]
    if start is None or end is None or step is None:
        raise ValueError(column)
    return TimeSeries(
        time_range=TimeRange(start=int(start), end=int(end), step=int(step)),
        values=column[_COLUMN_HEADER_LENGTH:],
    )
