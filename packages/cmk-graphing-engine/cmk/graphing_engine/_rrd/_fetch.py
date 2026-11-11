#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

from cmk.graphing_engine._data._naming import MetricName, Service, SiteID
from cmk.graphing_engine._data._timeseries import TimeRange, TimeSeries

from ._edge_neighbours import expected_served_step, with_edge_neighbours
from ._metrics import ConsolidationFunction, RRDMetric


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


@dataclass(frozen=True, kw_only=True)
class PerformanceDataRow:
    service: Service
    site_id: SiteID
    perf_data: str
    check_command: str


class FetchPerformanceDataRowsProtocol(Protocol):
    def __call__(
        self, services: Sequence[Service], *, only_site: SiteID | None
    ) -> Sequence[PerformanceDataRow]: ...


class FetchRRDTimeSeriesProtocol(Protocol):
    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
        only_site: SiteID | None,
    ) -> Mapping[RRDMetric, TimeSeries]: ...


@dataclass(frozen=True)
class TimeSeriesWithEdgeNeighbours:
    time_series_source: FetchRRDTimeSeriesProtocol
    now: float

    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
        only_site: SiteID | None,
    ) -> Mapping[RRDMetric, TimeSeries]:
        expected_step = expected_served_step(time_range, now=self.now)
        fetched = self._fetch_widened_by(
            expected_step,
            rrd_metrics,
            consolidation_function=consolidation_function,
            time_range=time_range,
            only_site=only_site,
        )
        served_step = max((series.time_range.step for series in fetched.values()), default=0)
        if served_step <= expected_step:
            return fetched
        return self._fetch_widened_by(
            served_step,
            rrd_metrics,
            consolidation_function=consolidation_function,
            time_range=time_range,
            only_site=only_site,
        )

    def _fetch_widened_by(
        self,
        neighbour_step: int,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
        only_site: SiteID | None,
    ) -> Mapping[RRDMetric, TimeSeries]:
        return self.time_series_source(
            rrd_metrics,
            consolidation_function=consolidation_function,
            time_range=with_edge_neighbours(time_range, neighbour_step),
            only_site=only_site,
        )
