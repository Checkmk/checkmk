#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine._data._fetched import FetchedData, PerformanceData
from cmk.graphing_engine._data._timeseries import merge_series, scaled_series, TimeRange, TimeSeries
from cmk.graphing_engine._quantities._quantity import MetricProtocol
from cmk.graphing_engine._rrd._fetch import (
    FetchPerformanceDataRowsProtocol,
    FetchRRDTimeSeriesProtocol,
)
from cmk.graphing_engine._rrd._metrics import ConsolidationFunction, RRDMetric
from cmk.graphing_engine._rrd._naming import Service, SiteID
from cmk.graphing_engine._rrd._performance_data import parse_performance_data, RawPerformanceData
from cmk.graphing_engine._rrd._resample import resample

from ._translations import rrd_originals, translate_performance_data


def _assembled(
    rrd_metrics: Sequence[RRDMetric],
    performance_data: Mapping[RRDMetric, PerformanceData],
    time_series: Mapping[RRDMetric, TimeSeries],
) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
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
) -> Mapping[SiteID | None, Sequence[RRDMetric]]:
    groups: dict[SiteID | None, list[RRDMetric]] = {}
    for metric in rrd_metrics:
        groups.setdefault(metric.site_id, []).append(metric)
    return groups


def _service_of(metric: RRDMetric) -> Service:
    return Service(host_name=metric.host_name, service_name=metric.service_name)


def _chop_last_empty_step(
    time_series: Mapping[RRDMetric, TimeSeries], end: int, *, now: float
) -> Mapping[RRDMetric, TimeSeries]:
    if not time_series:
        return time_series
    step = next(iter(time_series.values())).time_range.step
    if step <= 0 or abs(now - end) > step:
        return time_series
    if not all(series.values and series.values[-1] is None for series in time_series.values()):
        return time_series
    return {
        metric: TimeSeries(
            time_range=TimeRange(
                start=series.time_range.start, end=series.time_range.end - step, step=step
            ),
            values=series.values[:-1],
        )
        for metric, series in time_series.items()
    }


@dataclass(frozen=True, kw_only=True)
class RRDFetchData:
    consolidation_function: ConsolidationFunction
    registered_translations: Sequence[translations_v1.Translation]
    performance_data_source: FetchPerformanceDataRowsProtocol
    time_series_source: FetchRRDTimeSeriesProtocol
    now: float
    debug: bool
    logger: logging.Logger

    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        time_range: TimeRange,
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
        rrd_metrics = [metric for metric in metrics if isinstance(metric, RRDMetric)]
        raw_performance_data, site_of_service = self._fetch_performance_data(rrd_metrics)
        return _assembled(
            rrd_metrics,
            self._translated_performance_data(rrd_metrics, raw_performance_data),
            self._time_series(
                rrd_metrics, raw_performance_data, site_of_service, time_range=time_range
            ),
        )

    def _translated_performance_data(
        self,
        rrd_metrics: Sequence[RRDMetric],
        raw_performance_data: Mapping[tuple[SiteID | None, Service], RawPerformanceData],
    ) -> Mapping[RRDMetric, PerformanceData]:
        translated = {
            location: translate_performance_data(
                raw.check_command, raw.values, self.registered_translations
            )
            for location, raw in raw_performance_data.items()
        }
        performance_data: dict[RRDMetric, PerformanceData] = {}
        for metric in rrd_metrics:
            location = (metric.site_id, _service_of(metric))
            if location not in translated:
                continue
            if (data := translated[location].get(metric.metric_name)) is not None:
                performance_data[metric] = data
        return performance_data

    def _time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        raw_performance_data: Mapping[tuple[SiteID | None, Service], RawPerformanceData],
        site_of_service: Mapping[Service, SiteID],
        *,
        time_range: TimeRange,
    ) -> Mapping[RRDMetric, TimeSeries]:
        originals_by_metric: dict[
            RRDMetric, tuple[ConsolidationFunction, list[tuple[RRDMetric, float]]]
        ] = {}
        for metric in rrd_metrics:
            service = _service_of(metric)
            if (raw := raw_performance_data.get((metric.site_id, service))) is None:
                continue
            site_id = metric.site_id or site_of_service.get(service)
            function = metric.consolidation_function or self.consolidation_function
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
        return _chop_last_empty_step(time_series, reference.end, now=self.now)

    def _fetch_performance_data(
        self, rrd_metrics: Sequence[RRDMetric]
    ) -> tuple[
        Mapping[tuple[SiteID | None, Service], RawPerformanceData],
        Mapping[Service, SiteID],
    ]:
        result: dict[tuple[SiteID | None, Service], RawPerformanceData] = {}
        site_of_service: dict[Service, SiteID] = {}
        for group_site, site_metrics in _grouped_by_site(rrd_metrics).items():
            site_services = tuple(dict.fromkeys(_service_of(metric) for metric in site_metrics))
            if not site_services:
                continue
            for row in self.performance_data_source(site_services, only_site=group_site):
                result[(group_site, row.service)] = parse_performance_data(
                    row.perf_data, row.check_command, debug=self.debug, logger=self.logger
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
