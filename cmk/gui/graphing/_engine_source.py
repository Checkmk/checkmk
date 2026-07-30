#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The edition's implementations of the engine's source protocols: the livestatus reads a graph's
# data comes from, and the fetch that assembles them into what the engine evaluates. The pure
# ingredients live beside it - perf-data parsing in _engine_perfdata, translation resolution in
# _engine_translations, series alignment in _engine_series.


import contextlib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, Protocol

from cmk.ccc.site import SiteId
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    MetricName,
    MetricProtocol,
    PerformanceData,
    RRDMetric,
    Service,
    ServiceName,
    TimeRange,
    TimeSeries,
)
from cmk.graphing_engine import (
    SiteID as EngineSiteID,
)
from cmk.gui import sites
from cmk.livestatus_client import LivestatusColumn, lqencode, MKLivestatusNotFoundError
from cmk.livestatus_client.tables.services import Services

from ._engine_perfdata import parse_performance_data, RawPerformanceData
from ._engine_series import chop_last_empty_step, merge_series, resample, scaled_series
from ._engine_translations import (
    map_metric_names,
    rrd_originals,
    translate_performance_data,
)

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
                        perf_data_string, check_command, rrd_metrics, debug=self.debug
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


@dataclass(frozen=True, kw_only=True)
class PerformanceDataRow:
    service: Service
    site_id: EngineSiteID
    perf_data: str
    check_command: str


class _RRDFetchPerformanceDataProtocol(Protocol):
    def __call__(
        self, services: Sequence[Service], *, only_site: EngineSiteID | None
    ) -> Sequence[PerformanceDataRow]: ...


class _RRDFetchTimeSeriesProtocol(Protocol):
    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
        only_site: EngineSiteID | None,
    ) -> Mapping[RRDMetric, TimeSeries]: ...


@dataclass(frozen=True)
class RRDFetchPerformanceData:
    def __call__(
        self, services: Sequence[Service], *, only_site: EngineSiteID | None
    ) -> Sequence[PerformanceDataRow]:
        # prepend_site reveals which site each row came from (as in the legacy fetch_graph_row): a
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
                self._column(
                    MetricName(name),
                    consolidation_function=consolidation_function,
                    time_range=time_range,
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
                            if not column:
                                continue
                            result[metric] = TimeSeries(
                                time_range=TimeRange(
                                    start=int(column[0]), end=int(column[1]), step=int(column[2])
                                ),
                                values=column[3:],
                            )
        return result

    def _column(
        self,
        metric_name: MetricName,
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> str:
        data_range_args: list[int] = [time_range.start, time_range.end, max(1, time_range.step)]
        if self.max_data_points is not None:
            data_range_args.append(self.max_data_points)
        # `rrddata` is registered on both the hosts and the services table and the composed column
        # name is the same on either, so building it via Services is fine even for the hosts query
        # that _object_queries emits. `dynamic` validates all parts via LqSafe.
        return Services.rrddata.dynamic(
            metric_name, f"{metric_name}.{consolidation_function}", *data_range_args
        ).name


@dataclass(frozen=True, kw_only=True)
class QueryLimitReached:
    # A fan-out query hit its backend series cap, so its result is truncated.
    metric_name: str
    max_series: int
    num_series: int


@dataclass
class FetchDiagnostics:
    # Non-fatal fetch diagnostics surfaced to the caller: query series caps that were hit and
    # per-query fetch errors. Only the metric-backend fetch fills these today; the RRD fetch leaves
    # them empty. Mutable so the fetch can accumulate into it while resolving the data.
    limits_reached: list[QueryLimitReached] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def assemble_fetched_data(
    rrd_metrics: Sequence[RRDMetric],
    performance_data: Mapping[RRDMetric, PerformanceData],
    time_series: Mapping[RRDMetric, TimeSeries],
) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
    # A metric the fetch resolved neither performance data nor a series for is left out altogether,
    # so the quantity evaluates as absent rather than as an empty curve.
    assembled: dict[MetricProtocol, Sequence[FetchedData]] = {}
    for metric in rrd_metrics:
        data = performance_data.get(metric)
        series = time_series.get(metric)
        if data is None and series is None:
            continue
        assembled[metric] = [FetchedData(performance_data=data, time_series=series)]
    return assembled


def _grouped_by_site(
    rrd_metrics: Sequence[RRDMetric],
) -> Mapping[EngineSiteID | None, Sequence[RRDMetric]]:
    # Group by the metric's own site (None when unknown). A same host/service on two sites is thereby
    # kept apart - both as distinct fetch groups and as distinct performance-data keys.
    groups: dict[EngineSiteID | None, list[RRDMetric]] = {}
    for metric in rrd_metrics:
        groups.setdefault(metric.site_id, []).append(metric)
    return groups


@dataclass(frozen=True)
class RRDFetchData:
    debug: bool
    registered_translations: Sequence[translations_v1.Translation] = ()
    # Where the two reads this fetch is built on come from. The defaults are the monitoring core;
    # what the fetch does with the data - translate it, resolve the columns a metric is drawn from,
    # scale and merge the series - sits above them and is independent of it.
    performance_data_source: _RRDFetchPerformanceDataProtocol = RRDFetchPerformanceData()
    time_series_source: _RRDFetchTimeSeriesProtocol = RRDFetchTimeSeries()
    # Accumulated while fetching; read by the dispatcher into the evaluated result.
    diagnostics: FetchDiagnostics = field(default_factory=FetchDiagnostics, compare=False)

    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
        rrd_metrics = [metric for metric in metrics if isinstance(metric, RRDMetric)]
        raw_performance_data, site_of_service = self._fetch_performance_data(rrd_metrics)
        performance_data = self._translated_performance_data(rrd_metrics, raw_performance_data)
        time_series = self._time_series(
            rrd_metrics,
            raw_performance_data,
            site_of_service,
            consolidation_function=consolidation_function,
            time_range=time_range,
        )
        return assemble_fetched_data(rrd_metrics, performance_data, time_series)

    def _translated_performance_data(
        self,
        rrd_metrics: Sequence[RRDMetric],
        raw_performance_data: Mapping[tuple[EngineSiteID | None, Service], RawPerformanceData],
    ) -> Mapping[RRDMetric, PerformanceData]:
        translated = {
            location: translate_performance_data(
                raw.check_command, raw.values, self.registered_translations
            )
            for location, raw in raw_performance_data.items()
        }
        performance_data: dict[RRDMetric, PerformanceData] = {}
        for metric in rrd_metrics:
            location = (
                metric.site_id,
                Service(host_name=metric.host_name, service_name=metric.service_name),
            )
            if location not in translated:
                continue
            if (data := translated[location].get(metric.metric_name)) is not None:
                performance_data[metric] = data
        return performance_data

    def _time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        raw_performance_data: Mapping[tuple[EngineSiteID | None, Service], RawPerformanceData],
        site_of_service: Mapping[Service, EngineSiteID],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[RRDMetric, TimeSeries]:
        originals_by_metric: dict[
            RRDMetric, tuple[ConsolidationFunction, list[tuple[RRDMetric, float]]]
        ] = {}
        for metric in rrd_metrics:
            service = Service(host_name=metric.host_name, service_name=metric.service_name)
            if (raw := raw_performance_data.get((metric.site_id, service))) is None:
                continue
            # A metric that already carries its site keeps it; otherwise use the site resolved while
            # fetching the performance data, so the RRD fetch is scoped to it.
            site_id = metric.site_id or site_of_service.get(service)
            function = metric.consolidation_function or consolidation_function
            originals_by_metric[metric] = (
                function,
                [
                    (
                        RRDMetric(
                            site_id=site_id,
                            host_name=metric.host_name,
                            service_name=metric.service_name,
                            metric_name=original.metric_name,
                        ),
                        original.scale,
                    )
                    for original in rrd_originals(
                        metric.metric_name, raw, self.registered_translations
                    )
                ],
            )

        raw_by_function: dict[ConsolidationFunction, Mapping[RRDMetric, TimeSeries]] = {}
        for function in dict.fromkeys(func for func, _ in originals_by_metric.values()):
            raw_by_function[function] = self._fetch_time_series(
                list(
                    dict.fromkeys(
                        rrd_metric
                        for func, originals in originals_by_metric.values()
                        if func == function
                        for rrd_metric, _scale in originals
                    )
                ),
                consolidation_function=function,
                time_range=time_range,
            )

        # The reference grid is the first fetched source series in drawn order. The RRD backend snaps
        # the requested start/end/step, so every series is aligned to this shared grid - not the
        # request - which is what the curves and any arithmetic across them line up on (matching the
        # legacy pipeline, which aligns everything to the first fetched RRD's returned grid).
        reference = next(
            (
                ts.time_range
                for function, originals in originals_by_metric.values()
                for rrd_metric, _scale in originals
                if (ts := raw_by_function[function].get(rrd_metric)) is not None
            ),
            None,
        )
        if reference is None:
            return {}

        time_series: dict[RRDMetric, TimeSeries] = {}
        for metric, (function, originals) in originals_by_metric.items():
            scaled = [
                scaled_series(resample(ts, reference, function), scale)
                for rrd_metric, scale in originals
                if (ts := raw_by_function[function].get(rrd_metric)) is not None
            ]
            if scaled:
                time_series[metric] = merge_series(scaled, reference)
        return chop_last_empty_step(time_series, reference.end)

    def _fetch_performance_data(
        self, rrd_metrics: Sequence[RRDMetric]
    ) -> tuple[
        Mapping[tuple[EngineSiteID | None, Service], RawPerformanceData],
        Mapping[Service, EngineSiteID],
    ]:
        result: dict[tuple[EngineSiteID | None, Service], RawPerformanceData] = {}
        site_of_service: dict[Service, EngineSiteID] = {}
        for group_site, site_metrics in _grouped_by_site(rrd_metrics).items():
            site_services = tuple(
                dict.fromkeys(
                    Service(host_name=metric.host_name, service_name=metric.service_name)
                    for metric in site_metrics
                )
            )
            if not site_services:
                continue
            # The performance data is keyed by the metric's own site, so a same host/service matched
            # on two sites keeps a distinct entry per site.
            for row in self.performance_data_source(site_services, only_site=group_site):
                result[(group_site, row.service)] = parse_performance_data(
                    row.perf_data, row.check_command, debug=self.debug
                )
                site_of_service[row.service] = row.site_id
        return result, site_of_service

    def _fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, TimeSeries]:
        result: dict[RRDMetric, TimeSeries] = {}
        for group_site, site_metrics in _grouped_by_site(rrd_metrics).items():
            result.update(
                self.time_series_source(
                    site_metrics,
                    consolidation_function=consolidation_function,
                    time_range=time_range,
                    only_site=group_site,
                )
            )
        return result
