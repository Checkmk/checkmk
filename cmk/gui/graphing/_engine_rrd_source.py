#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import contextlib
import re
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from livestatus import lqencode, MKLivestatusNotFoundError

from cmk.ccc.site import SiteId
from cmk.graphing_engine import (
    ConsolidationFunction,
    MetricName,
    PerformanceData,
    PerformanceValue,
    RRDMetric,
    ServiceRef,
    TimeRange,
)
from cmk.graphing_engine import (
    TimeSeries as EngineTimeSeries,
)
from cmk.gui import sites
from cmk.gui.log import logger

# Perf-data parsing duplicated from the legacy cmk.gui.graphing._translated_metrics, so this engine
# RRD source stays independent of the legacy graphing stack (the duplication is intentional). Only the
# eight fields the engine consumes are kept; the legacy lookup-name / unit handling is dropped.
_VALUE_AND_UNIT = re.compile(r"([0-9.,-]*)(.*)")


@dataclass(frozen=True)
class _PerfEntry:
    metric_name: MetricName
    value: float
    warn: float | None
    crit: float | None
    warn_lower: float | None
    crit_lower: float | None
    min_: float | None
    max_: float | None


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
    """Nagios range notation → (lower, upper): "10"→(None,10), "1:10"→(1,10), "10:"→(10,None)."""
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
    assert value_and_unit is not None  # the regex always matches
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
) -> tuple[list[_PerfEntry], str]:
    """Convert perf_data_string into perf entries and extract the (normalized) check command."""
    check_command = _parse_check_command(check_command)

    parts = shlex.split(perf_data_string)
    # A PNP-style check command may be appended in brackets.
    if parts and parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]
    check_command = check_command.replace(".", "_")  # cf. maincheckify

    perf_data: list[_PerfEntry] = []
    for part in parts:
        try:
            varname, value_text, value_parts = _parse_perf_values(part)
            value, unit_name = _split_unit(value_text)
            if value is None or unit_name is None:
                continue  # ignore useless empty variable
            warn_lower, warn = _parse_range(value_parts[0])
            crit_lower, crit = _parse_range(value_parts[1])
            perf_data.append(
                _PerfEntry(
                    metric_name=MetricName(varname),
                    value=value,
                    warn=warn,
                    crit=crit,
                    warn_lower=warn_lower,
                    crit_lower=crit_lower,
                    min_=_float_or_int(value_parts[2]),
                    max_=_float_or_int(value_parts[3]),
                )
            )
        except Exception as exc:
            logger.exception("Failed to parse perfdata '%s'", perf_data_string)
            if debug:
                raise exc
    return perf_data, check_command


@dataclass(frozen=True)
class EngineRRDSource:
    site_id: SiteId | None
    debug: bool

    @staticmethod
    def parse_performance_data(
        perf_data_string: str,
        check_command: str,
        rrd_metrics: Sequence[str] = (),
        *,
        debug: bool,
    ) -> PerformanceData:
        perf_data, normalized_check_command = _parse_perf_data(
            perf_data_string, check_command, debug=debug
        )
        # Merge metric names present in RRD but absent from the current perf_data (as synthetic value=1
        # entries) so their graphs still appear — legacy parity (cf. compute_translated_metrics).
        if rrd_metrics:
            rrd_only, _command = _parse_perf_data(
                " ".join(f'"{m}"=1' if " " in m else f"{m}=1" for m in rrd_metrics if "," not in m),
                check_command,
                debug=debug,
            )
            present = {entry.metric_name for entry in perf_data}
            perf_data = [*perf_data, *(e for e in rrd_only if e.metric_name not in present)]
        return PerformanceData(
            check_command=normalized_check_command,
            values=[
                PerformanceValue(
                    metric_name=entry.metric_name,
                    value=entry.value,
                    warning=entry.warn,
                    critical=entry.crit,
                    lower_warning=entry.warn_lower,
                    lower_critical=entry.crit_lower,
                    minimum=entry.min_,
                    maximum=entry.max_,
                )
                for entry in perf_data
            ],
        )

    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]:
        unique = list(dict.fromkeys(services))
        if not unique:
            return {}
        # One livestatus query for the whole service set: an OR over the (host, service) pairs. The
        # host_name / description columns identify which service each row belongs to.
        query = "GET services\nColumns: host_name description perf_data metrics check_command\n"
        for service in unique:
            query += f"Filter: host_name = {lqencode(service.host_name)}\n"
            query += f"Filter: description = {lqencode(service.service_name)}\n"
            query += "And: 2\n"
        if len(unique) > 1:
            query += f"Or: {len(unique)}\n"
        result: dict[ServiceRef, PerformanceData] = {}
        with sites.only_sites(self.site_id):
            for (
                host_name,
                description,
                perf_data_string,
                rrd_metrics,
                check_command,
            ) in sites.live().query(query):
                result[ServiceRef(host_name=host_name, service_name=description)] = (
                    self.parse_performance_data(
                        perf_data_string, check_command, rrd_metrics, debug=self.debug
                    )
                )
        return {service: result[service] for service in unique if service in result}

    def fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, EngineTimeSeries]:
        # The raw RRD column of every metric, unscaled (the engine scales and merges the originals
        # itself). Services requesting the same set of metric names share one livestatus query — so a
        # combined graph (the same metric on every service) is fetched in a single query. Columns must
        # be uniform per query, hence the grouping by metric-name set rather than one query for all.
        metrics_by_service: dict[ServiceRef, list[RRDMetric]] = {}
        for metric in rrd_metrics:
            ref = ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
            metrics_by_service.setdefault(ref, []).append(metric)

        services_by_metric_names: dict[tuple[str, ...], list[ServiceRef]] = {}
        for ref, metrics in metrics_by_service.items():
            names = tuple(sorted(str(metric.metric_name) for metric in metrics))
            services_by_metric_names.setdefault(names, []).append(ref)

        result: dict[RRDMetric, EngineTimeSeries] = {}
        for metric_names, refs in services_by_metric_names.items():
            column_of = {name: index for index, name in enumerate(metric_names)}
            # ConsolidationFunction is a StrEnum, so it renders as its "max"/"min"/"average" value.
            data_range = f"{time_range.start}:{time_range.end}:{max(1, time_range.step)}"
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
            with sites.only_sites(self.site_id), contextlib.suppress(MKLivestatusNotFoundError):
                for row in sites.live().query(query):
                    ref = ServiceRef(host_name=row[0], service_name=row[1])
                    # The columns come back on RRDTool's native grid; the engine aligns them to the
                    # requested time range itself, so hand them over as fetched.
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
