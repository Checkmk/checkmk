#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Protocol

from ._fetched import FetchedData
from ._naming import MetricName, Service
from ._quantity import MetricProtocol
from ._timeseries import TimeRange


class FetchMetricNamesProtocol(Protocol):
    def __call__(self) -> Mapping[Service, frozenset[MetricName]]: ...


class FetchDataProtocol(Protocol):
    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        time_range: TimeRange,
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]: ...


def fetched_time_range(
    fetched: Mapping[MetricProtocol, Sequence[FetchedData]], *, fallback: TimeRange
) -> TimeRange:
    return next(
        (
            data.time_series.time_range
            for series in fetched.values()
            for data in series
            if data.time_series is not None
        ),
        fallback,
    )
