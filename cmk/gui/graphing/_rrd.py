#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Core for getting the actual raw data points via Livestatus from RRD"""

# mypy: disable-error-code="comparison-overlap"

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache

import cmk.ccc.version as cmk_version
from cmk import trace
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import parse_check_mk_version
from cmk.gui import sites
from cmk.gui.i18n import _
from cmk.gui.type_defs import ColumnName
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.livestatus_client import livestatus_lql
from cmk.livestatus_client.tables.services import Services
from cmk.livestatus_client.types import Column, DynamicColumn
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from ._from_api import RegisteredMetric
from ._graph_metric_expressions import GraphConsolidationFunction
from ._legacy import (
    check_metrics,
    CheckMetricEntry,
)
from ._metrics import get_metric_spec
from ._time_series import TimeSeries
from ._translated_metrics import (
    compute_translated_metrics,
    find_matching_translation,
    parse_perf_data,
    TranslatedMetric,
    TranslationSpec,
)
from ._unit import user_specific_unit

tracer = trace.get_tracer()


@dataclass(frozen=True)
class HostGraphRow:
    site_id: SiteId
    host_name: HostName
    check_command: str
    translated_metrics: Mapping[str, TranslatedMetric] = field(default_factory=dict)

    @property
    def service_name(self) -> ServiceName:
        return ServiceName("_HOST_")


@dataclass(frozen=True)
class ServiceGraphRow:
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    check_command: str
    translated_metrics: Mapping[str, TranslatedMetric] = field(default_factory=dict)


@tracer.instrument("graphing.fetch_graph_row")
def fetch_graph_row(
    site_id: list[SiteId] | SiteId | None,
    host_name: HostName,
    service_description: ServiceName,
    registered_metrics: Mapping[str, RegisteredMetric],
    explicit_color: str = "",
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> HostGraphRow | ServiceGraphRow:
    columns = ["perf_data", "metrics", "check_command"]
    query = livestatus_lql([host_name], columns, service_description)
    what = "host" if service_description == "_HOST_" else "service"
    labels = [f"{what}_{col}" for col in columns]

    with sites.only_sites(site_id), sites.prepend_site():
        site, *values = sites.live().query_row(query)

    raw = dict(zip(labels, values))
    return make_graph_row(
        SiteId(site),
        host_name,
        service_description,
        raw[f"{what}_perf_data"],
        raw[f"{what}_metrics"],
        raw[f"{what}_check_command"],
        registered_metrics,
        explicit_color,
        debug=debug,
        temperature_unit=temperature_unit,
    )


def make_graph_row(
    site: SiteId,
    host_name: HostName,
    service_name: ServiceName,
    perf_data_string: str,
    metrics: list[MetricName],
    check_command: str,
    registered_metrics: Mapping[str, RegisteredMetric],
    explicit_color: str = "",
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> HostGraphRow | ServiceGraphRow:
    perf_data, normalized_check_command = parse_perf_data(
        perf_data_string, check_command, debug=debug
    )
    translated = compute_translated_metrics(
        perf_data,
        metrics,
        normalized_check_command,
        registered_metrics,
        explicit_color,
        debug=debug,
        temperature_unit=temperature_unit,
    )
    if service_name == "_HOST_":
        return HostGraphRow(
            site_id=site,
            host_name=host_name,
            check_command=normalized_check_command,
            translated_metrics=translated,
        )
    return ServiceGraphRow(
        site_id=site,
        host_name=host_name,
        service_name=service_name,
        check_command=normalized_check_command,
        translated_metrics=translated,
    )


@dataclass(frozen=True, kw_only=True)
class MetricProperties:
    metric_name: str
    consolidation_function: GraphConsolidationFunction  # effective, used for RPN query
    key_consolidation_function: GraphConsolidationFunction | None = (
        None  # original, used for rrd_data key
    )
    scale: float


def _rrd_columns(
    rrddata: DynamicColumn,
    metric_props: Iterable[MetricProperties],
    *,
    start_time: float,
    end_time: float,
    step: int | str,
) -> Iterator[Column]:
    """RRD data columns for each metric

    Include scaling of metric directly in query"""
    for metric_prop in metric_props:
        rpn = f"{metric_prop.metric_name}.{metric_prop.consolidation_function}"
        if metric_prop.scale != 1.0:
            rpn += ",%f,*" % metric_prop.scale
        # `step` may be a preformatted, colon separated step length & point count
        yield rrddata.dynamic(metric_prop.metric_name, rpn, start_time, end_time, step)


def _reverse_translate_into_all_potentially_relevant_metrics(
    canonical_name: MetricName,
    current_version: int,
    translations: Iterable[Mapping[MetricName, CheckMetricEntry]],
) -> set[MetricName]:
    return {
        canonical_name,
        *(
            metric_name
            for trans in translations
            for metric_name, options in trans.items()
            if canonical_name == options.get("name")
            and (
                # From version check used unified metric, and thus deprecates old translation
                # added a complete stable release, that gives the customer about a year of data
                # under the appropriate metric name.
                # We should however get all metrics unified before Cmk 2.1
                parse_check_mk_version(deprecated) + 10000000
                if (deprecated := options.get("deprecated"))
                else current_version
            )
            >= current_version
            # Note: Reverse translations only work for 1-to-1-mappings, entries such as
            # "~.*rta": {"name": "rta", "scale": m},
            # cannot be reverse-translated, since multiple metric names are apparently mapped to a
            # single new name. This is a design flaw we currently have to live with.
            and not metric_name.startswith("~")
        ),
    }


@lru_cache
def _reverse_translate_into_all_potentially_relevant_metrics_cached(
    canonical_name: MetricName,
) -> set[MetricName]:
    return _reverse_translate_into_all_potentially_relevant_metrics(
        canonical_name,
        parse_check_mk_version(cmk_version.__version__),
        check_metrics.values(),
    )


def all_rrd_columns_potentially_relevant_for_metric(
    metric_name: MetricName,
    consolidation_function: GraphConsolidationFunction,
    start_time: int,
    end_time: int,
) -> Iterator[ColumnName]:
    # The consumers of these columns (painters, dashlets) use the column *names* both in their
    # queries and as keys to look up the values in the resulting rows, so yield the names here.
    yield from (
        ColumnName(column.name)
        for column in _rrd_columns(
            Services.rrddata,
            (
                MetricProperties(
                    metric_name=metric_name,
                    consolidation_function=consolidation_function or "max",  # type: ignore[unreachable]
                    # at this point, we do not yet know if there any potential scalings due to
                    # metric translations
                    scale=1,
                )
                for metric_name in _reverse_translate_into_all_potentially_relevant_metrics_cached(
                    metric_name
                )
            ),
            start_time=start_time,
            end_time=end_time,
            step=60,
        )
    )


def _first_value_present(values: Sequence[float | None]) -> float | None:
    return next((value for value in values if value is not None), None)


@tracer.instrument("graphing.translate_and_merge_rrd_columns")
def translate_and_merge_rrd_columns(
    target_metric: MetricName,
    rrd_columns: Iterable[tuple[str, Sequence[float | None]]],
    translations: Mapping[MetricName, TranslationSpec],
    registered_metrics: Mapping[str, RegisteredMetric],
    *,
    temperature_unit: TemperatureUnit,
) -> TimeSeries:
    relevant_ts = []

    for column_name, data in rrd_columns:
        if data is None:
            raise MKGeneralException(_("Cannot retrieve historic data with Nagios core"))
        if len(data) <= 3:
            continue

        metric_name = MetricName(column_name.split(":")[1])
        metric_translation = find_matching_translation(metric_name, translations)

        if metric_translation.name != target_metric:
            continue

        if data[0] is None or data[1] is None or data[2] is None:
            raise ValueError(data)

        def _scale(v: float, s: float = metric_translation.scale) -> float:
            return v * s

        relevant_ts.append(
            TimeSeries(
                start=int(data[0]),
                end=int(data[1]),
                step=int(data[2]),
                values=data[3:],
                conversion=_scale,
            )
        )

    if not relevant_ts:
        return TimeSeries(start=0, end=0, step=0, values=[])

    return TimeSeries(
        start=relevant_ts[0].start,
        end=relevant_ts[0].end,
        step=relevant_ts[0].step,
        values=[_first_value_present(tsp) for tsp in zip(*relevant_ts)],
        conversion=user_specific_unit(
            get_metric_spec(target_metric, registered_metrics).unit_spec, temperature_unit
        ).conversion,
    )
