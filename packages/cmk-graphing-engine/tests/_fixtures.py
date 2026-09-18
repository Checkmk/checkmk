#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What both the quantity and the graph evaluation tests build their input out of."""

from collections.abc import Mapping, Sequence

from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    MetricName,
    MetricProtocol,
    PerformanceData,
    RRDMetric,
    ServiceName,
    TimeRange,
    TimeSeries,
)

_TR = TimeRange(start=0, end=30, step=10)  # three data points


def _metric(name: str) -> RRDMetric:
    return RRDMetric(
        host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName(name)
    )


def _data(
    *,
    value: float | None,
    warning: float | None = None,
    critical: float | None = None,
    lower_warning: float | None = None,
    lower_critical: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> PerformanceData:
    return PerformanceData(
        value=value,
        warning=warning,
        critical=critical,
        lower_warning=lower_warning,
        lower_critical=lower_critical,
        minimum=minimum,
        maximum=maximum,
    )


def _time_series(*values: float | None) -> TimeSeries:
    return TimeSeries(time_range=_TR, values=list(values))


def _fetched(
    performance_data: Mapping[RRDMetric, PerformanceData],
    time_series: Mapping[RRDMetric, TimeSeries],
) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
    fetched: dict[MetricProtocol, Sequence[FetchedData]] = {}
    for metric in {*performance_data, *time_series}:
        fetched[metric] = [
            FetchedData(
                performance_data=performance_data.get(metric),
                time_series=time_series.get(metric),
            )
        ]
    return fetched


class _FakeRRDFetchData:
    def __init__(
        self, fetched: Mapping[MetricProtocol, Sequence[FetchedData]] | None = None
    ) -> None:
        self._fetched = fetched or {}

    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        consolidation_function: ConsolidationFunction,  # noqa: ARG002
        time_range: TimeRange,  # noqa: ARG002
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
        return {metric: self._fetched[metric] for metric in metrics if metric in self._fetched}
