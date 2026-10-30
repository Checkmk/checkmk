#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import contextlib
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from cmk.ccc.site import SiteId
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchPerformanceDataRowsProtocol,
    FetchRRDTimeSeriesProtocol,
    HostName,
    map_metric_names,
    MetricName,
    parse_performance_data,
    PerformanceDataRow,
    RRDFetchData,
    RRDMetric,
    Service,
    ServiceName,
    time_series_of_rrd_column,
    TimeRange,
    TimeSeries,
    TimeSeriesWithEdgeNeighbours,
)
from cmk.graphing_engine import (
    SiteID as EngineSiteID,
)
from cmk.gui import sites
from cmk.gui.log import logger
from cmk.livestatus_client import LivestatusColumn, lqencode, MKLivestatusNotFoundError

from ._evaluation_options import EvaluationOptions
from ._metric_data import (
    rrd_column_name,
)
from ._plugins import registered_translations

HOST_PSEUDO_SERVICE: Final = ServiceName("_HOST_")


def _service_or_filter(services: Sequence[Service]) -> str:
    query = ""
    for service in services:
        query += f"Filter: host_name = {lqencode(service.host_name)}\n"
        query += f"Filter: description = {lqencode(service.service_name)}\n"
        query += "And: 2\n"
    if len(services) > 1:
        query += f"Or: {len(services)}\n"
    return query


def _host_or_filter(services: Sequence[Service]) -> str:
    query = "".join(f"Filter: name = {lqencode(service.host_name)}\n" for service in services)
    if len(services) > 1:
        query += f"Or: {len(services)}\n"
    return query


@dataclass(frozen=True)
class _ObjectQuery:
    # One livestatus query over the table the requested objects live on - the table switch
    # livestatus_lql makes for the legacy fetch, on the same "_HOST_" sentinel. Host metrics live on
    # the hosts table, which has no description column, so they are filtered by host name alone.
    lql: str
    on_hosts_table: bool

    def parse_row(
        self, row: Sequence[LivestatusColumn], site_id: EngineSiteID | None = None
    ) -> tuple[Service, Sequence[LivestatusColumn]]:
        if self.on_hosts_table:
            service_name, num_keys = HOST_PSEUDO_SERVICE, 1
        else:
            service_name, num_keys = ServiceName(str(row[1])), 2
        return (
            Service(site_id=site_id, host_name=HostName(str(row[0])), service_name=service_name),
            row[num_keys:],
        )


def _object_queries(services: Sequence[Service], columns: Sequence[str]) -> Iterator[_ObjectQuery]:
    # A mixed set of host and service metrics needs one query per table.
    hosts: list[Service] = []
    matched: list[Service] = []
    for service in services:
        if service.service_name == HOST_PSEUDO_SERVICE:
            hosts.append(service)
        else:
            matched.append(service)
    if hosts:
        yield _ObjectQuery(
            lql=f"GET hosts\nColumns: name {' '.join(columns)}\n" + _host_or_filter(hosts),
            on_hosts_table=True,
        )
    if matched:
        yield _ObjectQuery(
            lql=f"GET services\nColumns: host_name description {' '.join(columns)}\n"
            + _service_or_filter(matched),
            on_hosts_table=False,
        )


def _only_sites(site: EngineSiteID | None) -> SiteId | None:
    return SiteId(site) if site is not None else None


@dataclass(frozen=True)
class RRDFetchMetricNameMapping:
    # The single service to resolve. Its site is an input because the same host/service can be
    # monitored by two sites: without a scope both are resolved, and a template graph - which is
    # single-service - cannot be built from two. A caller that knows the site (it painted a row, it
    # loaded a specification) passes it; None resolves across all sites the user may see.
    host_name: HostName
    service_name: ServiceName
    debug: bool
    site_id: SiteId | None = None
    registered_translations: Sequence[translations_v1.Translation] = ()

    def __call__(self) -> Mapping[Service, Mapping[MetricName, MetricName]]:
        result: dict[Service, Mapping[MetricName, MetricName]] = {}
        for query in _object_queries(
            [Service(host_name=self.host_name, service_name=self.service_name)],
            ["perf_data", "metrics", "check_command"],
        ):
            with sites.only_sites(self.site_id), sites.prepend_site():
                for row_site, *row in sites.live().query(query.lql):
                    service, values = query.parse_row(row, EngineSiteID(str(row_site)))
                    perf_data_string, rrd_metrics, check_command = values
                    raw = parse_performance_data(
                        perf_data_string,
                        check_command,
                        rrd_metrics,
                        debug=self.debug,
                        logger=logger,
                    )
                    result[service] = map_metric_names(
                        raw.check_command, list(raw.values), self.registered_translations
                    )
        return result


@dataclass(frozen=True)
class RRDFetchMetricNames:
    host_name: HostName
    service_name: ServiceName
    debug: bool
    site_id: SiteId | None = None
    registered_translations: Sequence[translations_v1.Translation] = ()

    def __call__(self) -> Mapping[Service, frozenset[MetricName]]:
        return {
            service: frozenset(mapping.values())
            for service, mapping in RRDFetchMetricNameMapping(
                host_name=self.host_name,
                service_name=self.service_name,
                debug=self.debug,
                site_id=self.site_id,
                registered_translations=self.registered_translations,
            )().items()
        }


@dataclass(frozen=True)
class RRDFetchPerformanceData:
    def __call__(
        self, services: Sequence[Service], *, only_site: EngineSiteID | None
    ) -> Sequence[PerformanceDataRow]:
        # prepend_site reveals which site each row came from: a
        # metric whose site is unknown up front is thereby scoped to the site its data lives on for
        # the time-series fetch.
        rows: list[PerformanceDataRow] = []
        for query in _object_queries(services, ["perf_data", "check_command"]):
            with sites.only_sites(_only_sites(only_site)), sites.prepend_site():
                for row_site, *row in sites.live().query(query.lql):
                    service, values = query.parse_row(row)
                    perf_data, check_command = values
                    rows.append(
                        PerformanceDataRow(
                            service=service,
                            site_id=EngineSiteID(str(row_site)),
                            perf_data=str(perf_data),
                            check_command=str(check_command),
                        )
                    )
        return rows


@dataclass(frozen=True)
class RRDFetchTimeSeries:
    # An optional RRDtool cap on the number of data points a time-series query returns, appended to
    # the rrddata range (as the legacy forecast fetch does). None leaves the point count uncapped.
    max_data_points: int | None = None

    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
        only_site: EngineSiteID | None,
    ) -> Mapping[RRDMetric, TimeSeries]:
        metrics_by_service: dict[Service, list[RRDMetric]] = {}
        for metric in rrd_metrics:
            ref = Service(host_name=metric.host_name, service_name=metric.service_name)
            metrics_by_service.setdefault(ref, []).append(metric)

        services_by_metric_names: dict[tuple[str, ...], list[Service]] = {}
        for ref, metrics in metrics_by_service.items():
            names = tuple(sorted(str(metric.metric_name) for metric in metrics))
            services_by_metric_names.setdefault(names, []).append(ref)

        result: dict[RRDMetric, TimeSeries] = {}
        for metric_names, refs in services_by_metric_names.items():
            column_of = {name: index for index, name in enumerate(metric_names)}
            columns = [
                rrd_column_name(
                    MetricName(name),
                    consolidation_function=consolidation_function,
                    time_range=time_range,
                    max_data_points=self.max_data_points,
                )
                for name in metric_names
            ]
            for query in _object_queries(refs, columns):
                with (
                    sites.only_sites(_only_sites(only_site)),
                    contextlib.suppress(MKLivestatusNotFoundError),
                ):
                    for row in sites.live().query(query.lql):
                        service, values = query.parse_row(row)
                        for metric in metrics_by_service.get(service, []):
                            column = values[column_of[str(metric.metric_name)]]
                            if column is None:
                                continue
                            if (series := time_series_of_rrd_column(column)) is not None:
                                result[metric] = series
        return result


@dataclass(frozen=True, kw_only=True)
class QueryLimitReached:
    # A fan-out query hit its backend series cap, so its result is truncated.
    metric_name: str
    max_series: int


@dataclass
class FetchDiagnostics:
    # Non-fatal fetch diagnostics surfaced to the caller: query series caps that were hit and
    # per-query fetch errors. Only the telemetry metrics fetch fills these today; the RRD fetch leaves
    # them empty. Mutable so the fetch can accumulate into it while resolving the data.
    limits_reached: list[QueryLimitReached] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def rrd_fetch_data(
    options: EvaluationOptions,
    performance_data_source: FetchPerformanceDataRowsProtocol,
    time_series_source: FetchRRDTimeSeriesProtocol,
    *,
    debug: bool,
) -> RRDFetchData:
    now = time.time()
    return RRDFetchData(
        consolidation_function=options.consolidation_function,
        registered_translations=registered_translations(),
        performance_data_source=performance_data_source,
        time_series_source=(
            TimeSeriesWithEdgeNeighbours(time_series_source, now=now)
            if options.include_edge_neighbours
            else time_series_source
        ),
        now=now,
        debug=debug,
        logger=logger,
    )
