#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import contextlib
import re
import shlex
import time
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean
from typing import assert_never

from cmk.ccc.site import SiteId
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    HostName,
    Metric,
    MetricName,
    PerformanceData,
    RRDMetric,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
    TimeSeries,
)
from cmk.graphing_engine import (
    TimeSeries as EngineTimeSeries,
)
from cmk.gui import sites
from cmk.gui.log import logger
from cmk.livestatus_client import lqencode, MKLivestatusNotFoundError


def _timestamps(time_range: TimeRange) -> Sequence[int]:
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
    time_series: TimeSeries,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> Sequence[float | None]:
    desired = _timestamps(time_range)
    resampled: list[float | None] = []
    bucket: list[float | None] = []
    index = 0
    for timestamp, value in zip(_timestamps(time_series.time_range), time_series.values):
        if index < len(desired) and timestamp > desired[index]:
            resampled.append(_aggregate(bucket, consolidation_function))
            bucket = []
            index += 1
        bucket.append(value)
    if (missing := len(desired) - len(resampled)) > 0:
        resampled.append(_aggregate(bucket, consolidation_function))
        resampled += [None] * (missing - 1)
    return resampled


def _forward_fill(time_series: TimeSeries, time_range: TimeRange) -> Sequence[float | None]:
    source = time_series.time_range
    last = len(time_series.values) - 1
    return [
        time_series.values[max(0, min((timestamp - source.start) // source.step, last))]
        for timestamp in range(time_range.start, time_range.end, time_range.step)
    ]


def _resample(
    time_series: TimeSeries,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> TimeSeries:
    if time_series.time_range == time_range:
        return time_series
    if not time_series.values or time_series.time_range.step <= 0:
        return TimeSeries(time_range=time_range, values=[None] * len(_timestamps(time_range)))
    values = (
        _downsample(time_series, time_range, consolidation_function)
        if time_range.step >= time_series.time_range.step
        else _forward_fill(time_series, time_range)
    )
    return TimeSeries(time_range=time_range, values=values)


def _scaled_series(time_series: TimeSeries, scale: float) -> TimeSeries:
    if scale == 1.0:
        return time_series
    return TimeSeries(
        time_range=time_series.time_range,
        values=[None if value is None else value * scale for value in time_series.values],
    )


def _merge_series(time_series: Sequence[TimeSeries], time_range: TimeRange) -> TimeSeries:
    return TimeSeries(
        time_range=time_range,
        values=[
            next((value for value in point if value is not None), None)
            for point in zip(*(member.values for member in time_series))
        ],
    )


@dataclass(frozen=True, kw_only=True)
class RawPerformanceValue:
    value: float
    warning: float | None = None
    critical: float | None = None
    lower_warning: float | None = None
    lower_critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, kw_only=True)
class RawPerformanceData:
    check_command: str
    values: Mapping[MetricName, RawPerformanceValue]


_PREDICT_PREFIXES = ("predict_lower_", "predict_")

type _TranslationSpec = (
    translations_v1.RenameTo | translations_v1.ScaleBy | translations_v1.RenameToAndScaleBy
)


@dataclass(frozen=True, kw_only=True)
class _RRDOriginal:
    metric_name: MetricName
    scale: float


def _normalize_check_command(
    check_command: (
        translations_v1.PassiveCheck
        | translations_v1.ActiveCheck
        | translations_v1.HostCheckCommand
        | translations_v1.NagiosPlugin
    ),
) -> str:
    match check_command:
        case translations_v1.PassiveCheck():
            name = check_command.name
            return name if name.startswith("check_mk-") else f"check_mk-{name}"
        case translations_v1.ActiveCheck():
            name = check_command.name
            return name if name.startswith("check_mk_active-") else f"check_mk_active-{name}"
        case translations_v1.HostCheckCommand():
            name = check_command.name
            return name if name.startswith("check-mk-") else f"check-mk-{name}"
        case translations_v1.NagiosPlugin():
            name = (
                check_command.name
                if check_command.name.startswith("check_")
                else f"check_{check_command.name}"
            )
            return name.replace(".", "_")
        case _:
            assert_never(check_command)


def _specs_for_command(
    check_command: str,
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[str, _TranslationSpec]:
    if not check_command:
        return {}

    def _matches(candidate: str) -> Mapping[str, _TranslationSpec]:
        merged: dict[str, _TranslationSpec] = {}
        for translation in registered_translations:
            if candidate in (_normalize_check_command(cmd) for cmd in translation.check_commands):
                merged.update(translation.translations)
        return merged

    if direct := _matches(check_command):
        return direct
    if check_command.startswith("check_mk-mgmt_"):
        return _matches(check_command.replace("check_mk-mgmt_", "check_mk-", 1))
    return {}


def _name_and_scale(old_name: MetricName, spec: _TranslationSpec) -> tuple[MetricName, float]:
    match spec:
        case translations_v1.RenameTo():
            return MetricName(spec.metric_name), 1.0
        case translations_v1.ScaleBy():
            return old_name, spec.factor
        case translations_v1.RenameToAndScaleBy():
            return MetricName(spec.metric_name), spec.factor
        case _:
            assert_never(spec)


def _split_predict_prefix(metric_name: str) -> tuple[str, str]:
    for prefix in _PREDICT_PREFIXES:
        if metric_name.startswith(prefix):
            return prefix, metric_name[len(prefix) :]
    return "", metric_name


def _find_name_and_scale(
    metric_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
) -> tuple[MetricName, float]:
    if (spec := specs.get(metric_name)) is not None:
        return _name_and_scale(metric_name, spec)
    for pattern, spec in specs.items():
        if pattern.startswith("~") and re.compile(pattern[1:]).match(metric_name):
            return _name_and_scale(metric_name, spec)
    return metric_name, 1.0


def _reverse_names(
    canonical_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
) -> Mapping[MetricName, float]:
    result: dict[MetricName, float] = {}
    for old_name, spec in specs.items():
        if old_name.startswith("~"):
            continue
        name, scale = _name_and_scale(MetricName(old_name), spec)
        if name == canonical_name:
            result[MetricName(old_name)] = scale
    return result


def _deprecated_originals(
    metric_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
    present: Collection[MetricName],
) -> Iterator[_RRDOriginal]:
    prefix, bare_name = _split_predict_prefix(metric_name)
    for old_name, scale in _reverse_names(MetricName(bare_name), specs).items():
        if (column := MetricName(f"{prefix}{old_name}")) not in present:
            yield _RRDOriginal(metric_name=column, scale=scale)


def _originals_for_metric_name(
    metric_name: MetricName,
    check_command: str,
    registered_translations: Sequence[translations_v1.Translation],
) -> Sequence[_RRDOriginal]:
    specs = _specs_for_command(check_command, registered_translations)
    return [
        _RRDOriginal(metric_name=metric_name, scale=1.0),
        *_deprecated_originals(metric_name, specs, {metric_name}),
    ]


def translate_metric_names(
    check_command: str,
    raw_metric_names: Sequence[MetricName],
    registered_translations: Sequence[translations_v1.Translation],
) -> frozenset[MetricName]:
    specs = _specs_for_command(check_command, registered_translations)
    names: set[MetricName] = set()
    for metric_name in raw_metric_names:
        prefix, bare_name = _split_predict_prefix(metric_name)
        name, _scale = _find_name_and_scale(MetricName(bare_name), specs)
        names.add(MetricName(f"{prefix}{name}"))
    return frozenset(names)


def _scaled(value: float | None, scale: float) -> float | None:
    return None if value is None else value * scale


def _translate_performance_data(
    check_command: str,
    raw_values: Mapping[MetricName, RawPerformanceValue],
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[MetricName, PerformanceData]:
    specs = _specs_for_command(check_command, registered_translations)
    scaled_by_name: dict[MetricName, tuple[RawPerformanceValue, float]] = {}
    for original_name, raw_value in raw_values.items():
        prefix, bare_name = _split_predict_prefix(original_name)
        name, scale = _find_name_and_scale(MetricName(bare_name), specs)
        scaled_by_name[MetricName(f"{prefix}{name}")] = (raw_value, scale)
    return {
        name: PerformanceData(
            value=_scaled(raw_value.value, scale),
            lower_warning=_scaled(raw_value.lower_warning, scale),
            lower_critical=_scaled(raw_value.lower_critical, scale),
            warning=_scaled(raw_value.warning, scale),
            critical=_scaled(raw_value.critical, scale),
            minimum=_scaled(raw_value.minimum, scale),
            maximum=_scaled(raw_value.maximum, scale),
        )
        for name, (raw_value, scale) in scaled_by_name.items()
    }


_VALUE_AND_UNIT = re.compile(r"([0-9.,-]*)(.*)")


def _float_or_int(val: str | None) -> int | float | None:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None


def _parse_range(val: str | None) -> tuple[float | None, float | None]:
    if not val:
        return None, None
    if ":" not in val:
        return None, _float_or_int(val)
    lower_str, upper_str = val.split(":", 1)
    return (
        _float_or_int(lower_str) if lower_str else None,
        _float_or_int(upper_str) if upper_str else None,
    )


def _split_unit(value_text: str) -> tuple[float | None, str | None]:
    if not value_text or value_text.isspace():
        return None, None
    value_and_unit = re.match(_VALUE_AND_UNIT, value_text)
    assert value_and_unit is not None
    return _float_or_int(value_and_unit[1]) if value_and_unit[1] else None, value_and_unit[2]


def _parse_perf_values(
    data_str: str,
) -> tuple[str, str, tuple[str | None, str | None, str | None, str | None]]:
    varname, values = data_str.split("=", 1)
    varname = varname.replace('"', "").replace("'", "")
    value_parts = values.split(";")
    value = value_parts.pop(0)
    num_fields = len(value_parts)
    return (
        varname,
        value,
        (
            value_parts[0] if num_fields > 0 else None,
            value_parts[1] if num_fields > 1 else None,
            value_parts[2] if num_fields > 2 else None,
            value_parts[3] if num_fields > 3 else None,
        ),
    )


def _parse_check_command(check_command: str) -> str:
    parts = check_command.split("!", 1)
    if parts[0] == "check-mk-custom" and len(parts) >= 2:
        if parts[1].startswith("check_ping") or "/check_ping" in parts[1]:
            return "check_ping"
    return parts[0]


def _parse_perf_data(
    perf_data_string: str, check_command: str, *, debug: bool
) -> tuple[Mapping[MetricName, RawPerformanceValue], str]:
    check_command = _parse_check_command(check_command)

    parts = shlex.split(perf_data_string)
    if parts and parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]
    check_command = check_command.replace(".", "_")

    raw_perf_data: dict[MetricName, RawPerformanceValue] = {}
    for part in parts:
        try:
            varname, value_text, value_parts = _parse_perf_values(part)
            value, unit_name = _split_unit(value_text)
            if value is None or unit_name is None:
                continue
            lower_warning, warning = _parse_range(value_parts[0])
            lower_critical, critical = _parse_range(value_parts[1])
            raw_perf_data[MetricName(varname)] = RawPerformanceValue(
                value=value,
                warning=warning,
                critical=critical,
                lower_warning=lower_warning,
                lower_critical=lower_critical,
                minimum=_float_or_int(value_parts[2]),
                maximum=_float_or_int(value_parts[3]),
            )
        except Exception as exc:
            logger.exception(
                "Failed to parse perfdata '%(perf_data_string)s'",
                {"perf_data_string": perf_data_string},
            )
            if debug:
                raise exc
    return raw_perf_data, check_command


def _service_or_filter(services: Sequence[Service]) -> str:
    query = ""
    for service in services:
        query += f"Filter: host_name = {lqencode(service.host_name)}\n"
        query += f"Filter: description = {lqencode(service.service_name)}\n"
        query += "And: 2\n"
    if len(services) > 1:
        query += f"Or: {len(services)}\n"
    return query


def parse_performance_data(
    perf_data_string: str,
    check_command: str,
    rrd_metrics: Sequence[str] = (),
    *,
    debug: bool,
) -> RawPerformanceData:
    raw_perf_data, normalized_check_command = _parse_perf_data(
        perf_data_string, check_command, debug=debug
    )
    if rrd_metrics:
        rrd_only, _command = _parse_perf_data(
            " ".join(f'"{m}"=1' if " " in m else f"{m}=1" for m in rrd_metrics if "," not in m),
            check_command,
            debug=debug,
        )
        raw_perf_data = {
            **raw_perf_data,
            **{name: value for name, value in rrd_only.items() if name not in raw_perf_data},
        }
    return RawPerformanceData(check_command=normalized_check_command, values=raw_perf_data)


@dataclass(frozen=True)
class EngineRRDFetchMetricNames:
    # The single service to resolve, identified by host and service name only: its site is not an
    # input but resolved from the livestatus rows (prepend_site), so a same host/service on two
    # sites yields two entries.
    host_name: HostName
    service_name: ServiceName
    debug: bool
    registered_translations: Sequence[translations_v1.Translation] = ()

    def __call__(self) -> Mapping[Service, frozenset[MetricName]]:
        query = (
            "GET services\nColumns: host_name description perf_data metrics check_command\n"
            f"Filter: host_name = {lqencode(self.host_name)}\n"
            f"Filter: description = {lqencode(self.service_name)}\n"
            "And: 2\n"
        )
        # prepend_site tags each row with the site its data lives on (as the legacy fetch does), so
        # each resolved service carries its real site - the site scope, if any, is the caller's
        # (an only_sites context). The graph built from these services thereby carries the site on
        # its metrics (for per-site fetching and tuning scoping), and a same host/service on two
        # sites is kept apart as two entries.
        result: dict[Service, frozenset[MetricName]] = {}
        with sites.prepend_site():
            for (
                row_site,
                host_name,
                description,
                perf_data_string,
                rrd_metrics,
                check_command,
            ) in sites.live().query(query):
                raw = parse_performance_data(
                    perf_data_string, check_command, rrd_metrics, debug=self.debug
                )
                service = Service(
                    site_id=SiteID(str(row_site)), host_name=host_name, service_name=description
                )
                result[service] = translate_metric_names(
                    raw.check_command, list(raw.values), self.registered_translations
                )
        return result


def _chop_last_empty_step(
    time_series: Mapping[RRDMetric, EngineTimeSeries], end: int
) -> Mapping[RRDMetric, EngineTimeSeries]:
    # Drop the empty trailing step of a graph that ends "now": the current RRD step has no data yet,
    # so an all-None last point across every curve is stripped rather than drawn as a gap (matches
    # the legacy _chop_last_empty_step).
    if not time_series:
        return time_series
    step = next(iter(time_series.values())).time_range.step
    if step <= 0 or abs(time.time() - end) > step:
        return time_series
    if not all(series.values and series.values[-1] is None for series in time_series.values()):
        return time_series
    return {
        metric: EngineTimeSeries(
            time_range=TimeRange(
                start=series.time_range.start, end=series.time_range.end - step, step=step
            ),
            values=series.values[:-1],
        )
        for metric, series in time_series.items()
    }


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


@dataclass(frozen=True)
class EngineRRDFetchData:
    debug: bool
    registered_translations: Sequence[translations_v1.Translation] = ()
    # An optional RRDtool cap on the number of data points a time-series query returns, appended to
    # the rrddata range (as the legacy forecast fetch does). None leaves the point count uncapped.
    max_data_points: int | None = None
    # Accumulated while fetching; read by the dispatcher into the evaluated result.
    diagnostics: FetchDiagnostics = field(default_factory=FetchDiagnostics, compare=False)

    def __call__(
        self,
        metrics: Sequence[Metric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[Metric, Sequence[FetchedData]]:
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
        result: dict[Metric, Sequence[FetchedData]] = {}
        for metric in rrd_metrics:
            data = performance_data.get(metric)
            series = time_series.get(metric)
            if data is None and series is None:
                continue
            result[metric] = [FetchedData(performance_data=data, time_series=series)]
        return result

    def _translated_performance_data(
        self,
        rrd_metrics: Sequence[RRDMetric],
        raw_performance_data: Mapping[tuple[SiteID | None, Service], RawPerformanceData],
    ) -> Mapping[RRDMetric, PerformanceData]:
        translated = {
            location: _translate_performance_data(
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
        raw_performance_data: Mapping[tuple[SiteID | None, Service], RawPerformanceData],
        site_of_service: Mapping[Service, SiteID],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[RRDMetric, EngineTimeSeries]:
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
                    for original in _originals_for_metric_name(
                        metric.metric_name, raw.check_command, self.registered_translations
                    )
                ],
            )

        raw_by_function: dict[ConsolidationFunction, Mapping[RRDMetric, EngineTimeSeries]] = {}
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

        time_series: dict[RRDMetric, EngineTimeSeries] = {}
        for metric, (function, originals) in originals_by_metric.items():
            scaled = [
                _scaled_series(_resample(ts, reference, function), scale)
                for rrd_metric, scale in originals
                if (ts := raw_by_function[function].get(rrd_metric)) is not None
            ]
            if scaled:
                time_series[metric] = _merge_series(scaled, reference)
        return _chop_last_empty_step(time_series, reference.end)

    def _group_by_site(
        self, rrd_metrics: Sequence[RRDMetric]
    ) -> Mapping[SiteID | None, Sequence[RRDMetric]]:
        # Group by the metric's own site (None when unknown). A same host/service on two sites is
        # thereby kept apart - both as distinct fetch groups and as distinct performance-data keys.
        groups: dict[SiteID | None, list[RRDMetric]] = {}
        for metric in rrd_metrics:
            groups.setdefault(metric.site_id, []).append(metric)
        return groups

    def _only_sites(self, site: SiteID | None) -> SiteId | None:
        # Scope a livestatus query to the metric's site when known (None = all sites, resolved by the
        # prepending fetch below).
        return SiteId(site) if site is not None else None

    def _fetch_performance_data(
        self, rrd_metrics: Sequence[RRDMetric]
    ) -> tuple[
        Mapping[tuple[SiteID | None, Service], RawPerformanceData], Mapping[Service, SiteID]
    ]:
        result: dict[tuple[SiteID | None, Service], RawPerformanceData] = {}
        site_of_service: dict[Service, SiteID] = {}
        for group_site, site_metrics in self._group_by_site(rrd_metrics).items():
            site_services = tuple(
                dict.fromkeys(
                    Service(host_name=metric.host_name, service_name=metric.service_name)
                    for metric in site_metrics
                )
            )
            if not site_services:
                continue
            query = (
                "GET services\nColumns: host_name description perf_data check_command\n"
                + _service_or_filter(site_services)
            )
            # prepend_site reveals which site each row came from (as in the legacy fetch_graph_row):
            # a metric whose site is unknown up front is thereby scoped to the site its data lives on
            # for the time-series fetch. The performance data is keyed by the metric's own site, so a
            # same host/service matched on two sites keeps a distinct entry per site.
            with sites.only_sites(self._only_sites(group_site)), sites.prepend_site():
                for (
                    row_site,
                    host_name,
                    description,
                    perf_data_string,
                    check_command,
                ) in sites.live().query(query):
                    service = Service(host_name=host_name, service_name=description)
                    result[(group_site, service)] = parse_performance_data(
                        perf_data_string, check_command, debug=self.debug
                    )
                    site_of_service[service] = SiteID(str(row_site))
        return result, site_of_service

    def _fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, EngineTimeSeries]:
        result: dict[RRDMetric, EngineTimeSeries] = {}
        for group_site, site_metrics in self._group_by_site(rrd_metrics).items():
            result.update(
                self._fetch_time_series_of_site(
                    site_metrics,
                    self._only_sites(group_site),
                    time_range=time_range,
                    consolidation_function=consolidation_function,
                )
            )
        return result

    def _fetch_time_series_of_site(
        self,
        rrd_metrics: Sequence[RRDMetric],
        site_id: SiteId | None,
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, EngineTimeSeries]:
        metrics_by_service: dict[Service, list[RRDMetric]] = {}
        for metric in rrd_metrics:
            ref = Service(host_name=metric.host_name, service_name=metric.service_name)
            metrics_by_service.setdefault(ref, []).append(metric)

        services_by_metric_names: dict[tuple[str, ...], list[Service]] = {}
        for ref, metrics in metrics_by_service.items():
            names = tuple(sorted(str(metric.metric_name) for metric in metrics))
            services_by_metric_names.setdefault(names, []).append(ref)

        result: dict[RRDMetric, EngineTimeSeries] = {}
        for metric_names, refs in services_by_metric_names.items():
            column_of = {name: index for index, name in enumerate(metric_names)}
            data_range = f"{time_range.start}:{time_range.end}:{max(1, time_range.step)}"
            if self.max_data_points is not None:
                data_range += f":{self.max_data_points}"
            columns = [
                f"rrddata:{name}:{name}.{consolidation_function}:{data_range}"
                for name in metric_names
            ]
            query = "GET services\nColumns: host_name description " + " ".join(columns) + "\n"
            for ref in refs:
                query += f"Filter: host_name = {lqencode(ref.host_name)}\n"
                query += f"Filter: description = {lqencode(ref.service_name)}\n"
                query += "And: 2\n"
            if len(refs) > 1:
                query += f"Or: {len(refs)}\n"
            with sites.only_sites(site_id), contextlib.suppress(MKLivestatusNotFoundError):
                for row in sites.live().query(query):
                    ref = Service(host_name=row[0], service_name=row[1])
                    for metric in metrics_by_service.get(ref, []):
                        column = row[2 + column_of[str(metric.metric_name)]]
                        if not column:
                            continue
                        result[metric] = EngineTimeSeries(
                            time_range=TimeRange(
                                start=int(column[0]), end=int(column[1]), step=int(column[2])
                            ),
                            values=column[3:],
                        )
        return result
