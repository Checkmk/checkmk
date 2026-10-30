#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What both the quantity and the graph evaluation tests build their input out of."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    MetricName,
    MetricProtocol,
    PerformanceData,
    RRDMetric,
    ServiceName,
    SiteID,
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
        time_range: TimeRange,  # noqa: ARG002
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
        return {metric: self._fetched[metric] for metric in metrics if metric in self._fetched}


_NOW = 1_800_000_000
_DAY = 24 * 60 * 60
_FIVE_MINUTES = 5 * 60
_MIDNIGHT_A_WEEK_AGO = (_NOW - 7 * _DAY) // _DAY * _DAY
_HALF_HOUR_A_WEEK_AGO = TimeRange(
    start=_MIDNIGHT_A_WEEK_AGO, end=_MIDNIGHT_A_WEEK_AGO + 30 * 60, step=60
)


@dataclass
class _FakeRRDWithOneArchive:
    archive_step: int
    asked_ranges: list[TimeRange] = field(default_factory=list)

    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,  # noqa: ARG002
        time_range: TimeRange,
        only_site: SiteID | None,  # noqa: ARG002
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.asked_ranges.append(time_range)
        start = time_range.start - time_range.start % self.archive_step
        end = time_range.end + -time_range.end % self.archive_step
        return {
            metric: TimeSeries(
                time_range=TimeRange(start=start, end=end, step=self.archive_step),
                values=[1.0] * ((end - start) // self.archive_step),
            )
            for metric in rrd_metrics
        }
