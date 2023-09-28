#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Core for getting the actual raw data points via Livestatus from RRD"""


import collections
import contextlib
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

import livestatus
from livestatus import SiteId

import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.prediction import livestatus_lql, TimeSeries, TimeSeriesValues
from cmk.utils.servicename import ServiceName

import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.type_defs import ColumnName

from ._graph_specification import (
    GraphMetric,
    MetricOpCombined,
    MetricOperation,
    MetricOpOperator,
    MetricOpRRDChoice,
    MetricOpRRDSource,
    MetricOpScalar,
    MetricOpTransformation,
)
from ._timeseries import op_func_wrapper, time_series_operators
from ._type_defs import GraphConsoldiationFunction
from ._unit_info import unit_info
from ._utils import (
    CheckMetricEntry,
    CombinedSingleMetricSpec,
    find_matching_translation,
    GraphDataRange,
    GraphRecipe,
    metric_info,
    reverse_translate_into_all_potentially_relevant_metrics_cached,
    RRDData,
    RRDDataKey,
)


def fetch_rrd_data_for_graph(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[GraphMetric]
    ],
) -> RRDData:
    unit_conversion = unit_info[graph_recipe.unit].get(
        "conversion",
        lambda v: v,
    )
    by_service = _group_needed_rrd_data_by_service(
        (
            entry.site_id,
            entry.host_name,
            entry.service_name,
            entry.metric_name,
            entry.consolidation_func_name,
            entry.scale,
        )
        for entry in get_needed_sources(graph_recipe.metrics, resolve_combined_single_metric_spec)
        if isinstance(entry, NeededElementForRRDDataKey)
    )
    rrd_data: RRDData = {}
    for (site, host_name, service_description), metrics in by_service.items():
        with contextlib.suppress(livestatus.MKLivestatusNotFoundError):
            for (perfvar, cf, scale), data in fetch_rrd_data(
                site, host_name, service_description, metrics, graph_recipe, graph_data_range
            ):
                rrd_data[(site, host_name, service_description, perfvar, cf, scale)] = TimeSeries(
                    data,
                    conversion=unit_conversion,
                )
    _align_and_resample_rrds(rrd_data, graph_recipe.consolidation_function)
    _chop_last_empty_step(graph_data_range, rrd_data)

    return rrd_data


def _align_and_resample_rrds(rrd_data: RRDData, cf: GraphConsoldiationFunction | None) -> None:
    """RRDTool aligns start/end/step to its internal precision.

    This is returned as first 3 values in each RRD data row. Using that
    info resampling and alignment is done in reference to the first metric.

    TimeSeries are mutated in place, argument rrd_data is thus mutated"""

    start_time = None
    end_time = None
    step = None

    for spec, rrddata in rrd_data.items():
        if not rrddata:
            spec_title = f"{spec[1]}/{spec[2]}/{spec[3]}"  # host/service/perfvar
            raise MKGeneralException(_("Cannot get RRD data for %s") % spec_title)

        if start_time is None:
            start_time, end_time, step = rrddata.twindow
        elif (start_time, end_time, step) != rrddata.twindow:
            rrddata.values = (
                rrddata.downsample((start_time, end_time, step), spec[4] or cf)
                if step >= rrddata.twindow[2]
                else rrddata.bfill_upsample((start_time, end_time, step), 0)
            )


# The idea is to omit the empty last step of graphs which are showing the
# last data which ends now (at the current time) where there is not yet
# data available for the current RRD step. Showing an empty space on the
# right of the graph seems a bit odd, so strip of the last (empty) step.
#
# This makes only sense for graphs which are ending "now". So disable this
# for the other graphs.
def _chop_last_empty_step(graph_data_range: GraphDataRange, rrd_data: RRDData) -> None:
    if not rrd_data:
        return

    sample_data = next(iter(rrd_data.values()))
    step = sample_data.twindow[2]
    # Disable graph chop for graphs which do not end within the current step
    if abs(time.time() - graph_data_range["time_range"][1]) > step:
        return

    # To avoid a gap when querying:
    # Chop one step from the end of the graph
    # `if` that is None for *all* curves(TimeSeries or graphs).
    if all(len(graph) and graph[-1] is None for graph in rrd_data.values()):
        _chop_end_of_the_curve(rrd_data, step)


def _chop_end_of_the_curve(rrd_data: RRDData, step: int) -> None:
    for data in rrd_data.values():
        del data.values[-1]
        data.end -= step


@dataclass(frozen=True)
class NeededElementForTranslation:
    host_name: HostName
    service_name: ServiceName


@dataclass(frozen=True)
class NeededElementForRRDDataKey:
    # TODO Intermediate step, will be cleaned up:
    # Relates to MetricOperation::rrd with SiteId, etc.
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: str
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float


def _needed_elements_of_expression(
    expression: MetricOperation,
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[GraphMetric]
    ],
) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
    if isinstance(expression, (MetricOpScalar, MetricOpRRDChoice)):
        yield NeededElementForTranslation(
            expression.host_name,
            expression.service_name,
        )

    elif isinstance(expression, (MetricOpOperator, MetricOpTransformation)):
        for operand in expression.operands:
            yield from _needed_elements_of_expression(operand, resolve_combined_single_metric_spec)

    elif isinstance(expression, MetricOpRRDSource):
        yield NeededElementForRRDDataKey(
            expression.site_id,
            expression.host_name,
            expression.service_name,
            expression.metric_name,
            expression.consolidation_func_name,
            expression.scale,
        )

    elif (
        isinstance(expression, MetricOpCombined)
        and cmk_version.edition() is not cmk_version.Edition.CRE
    ):
        if (cf := expression.single_metric_spec["consolidation_function"]) is None:
            raise TypeError(cf)

        metrics = resolve_combined_single_metric_spec(
            CombinedSingleMetricSpec(
                datasource=expression.single_metric_spec["datasource"],
                context=expression.single_metric_spec["context"],
                selected_metric=expression.single_metric_spec["selected_metric"],
                consolidation_function=cf,
                presentation=expression.single_metric_spec["presentation"],
            )
        )

        for out in (
            _needed_elements_of_expression(m.expression, resolve_combined_single_metric_spec)
            for m in metrics
        ):
            yield from out


def get_needed_sources(
    metrics: Sequence[GraphMetric],
    resolve_combined_single_metric_spec: Callable[
        [CombinedSingleMetricSpec], Sequence[GraphMetric]
    ],
    *,
    condition: Callable[[GraphMetric], bool] = lambda x: True,
) -> set[NeededElementForTranslation | NeededElementForRRDDataKey]:
    """Extract all metric data sources definitions

    metrics: List
        List of paint-able metrics, extract from defining expression needed metrics
    condition: Callable
        Filter function for metrics that are considered"""
    return {
        element
        for metric in metrics
        for element in _needed_elements_of_expression(
            metric.expression,
            resolve_combined_single_metric_spec,
        )
        if condition(metric)
    }


MetricProperties = tuple[str, GraphConsoldiationFunction | None, float]


def _group_needed_rrd_data_by_service(
    needed_rrd_data: Iterable[RRDDataKey],
) -> dict[tuple[SiteId, HostName, ServiceName], set[MetricProperties],]:
    by_service: dict[
        tuple[SiteId, HostName, ServiceName],
        set[MetricProperties],
    ] = collections.defaultdict(set)
    for site, host_name, service_description, perfvar, cf, scale in needed_rrd_data:
        by_service[(site, host_name, service_description)].add((perfvar, cf, scale))
    return by_service


def fetch_rrd_data(
    site: SiteId,
    host_name: HostName,
    service_description: ServiceName,
    metrics: set[MetricProperties],
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
) -> list[tuple[MetricProperties, TimeSeriesValues]]:
    start_time, end_time = graph_data_range["time_range"]

    step = graph_data_range["step"]
    # assumes str step is well formatted, colon separated step length & rrd point count
    if not isinstance(step, str):
        step = max(1, step)

    point_range = ":".join(map(str, (start_time, end_time, step)))
    lql_columns = list(rrd_columns(metrics, graph_recipe.consolidation_function, point_range))
    query = livestatus_lql([host_name], lql_columns, service_description)

    with sites.only_sites(site):
        return list(zip(metrics, sites.live().query_row(query)))


def rrd_columns(
    metrics: Iterable[MetricProperties],
    rrd_consolidation: GraphConsoldiationFunction | None,
    data_range: str,
) -> Iterator[ColumnName]:
    """RRD data columns for each metric

    Include scaling of metric directly in query"""

    for perfvar, cf, scale in metrics:
        cf = rrd_consolidation or cf or "max"
        rpn = f"{perfvar}.{cf}"
        if scale != 1.0:
            rpn += ",%f,*" % scale
        yield f"rrddata:{perfvar}:{rpn}:{data_range}"


def all_rrd_columns_potentially_relevant_for_metric(
    metric_name: MetricName,
    rrd_consolidation: GraphConsoldiationFunction,
    from_time: int,
    until_time: int,
) -> Iterator[ColumnName]:
    yield from rrd_columns(
        (
            (
                metric_name,
                None,
                # at this point, we do not yet know if there any potential scalings due to metric
                # translations
                1,
            )
            for metric_name in reverse_translate_into_all_potentially_relevant_metrics_cached(
                metric_name
            )
        ),
        rrd_consolidation,
        f"{from_time}:{until_time}:60",
    )


def translate_and_merge_rrd_columns(
    target_metric: MetricName,
    rrd_columms: Iterable[tuple[str, TimeSeriesValues]],
    translations: Mapping[MetricName, CheckMetricEntry],
) -> TimeSeries:
    def scaler(scale: float) -> Callable[[float], float]:
        return lambda v: v * scale

    relevant_ts = []

    for column_name, data in rrd_columms:
        if data is None:
            raise MKGeneralException(_("Cannot retrieve historic data with Nagios core"))
        if len(data) <= 3:
            continue

        metric_name = MetricName(column_name.split(":")[1])
        metric_translation = find_matching_translation(metric_name, translations)

        if metric_translation.get("name", metric_name) == target_metric:
            relevant_ts.append(
                TimeSeries(data, conversion=scaler(metric_translation.get("scale", 1)))
            )

    if not relevant_ts:
        return TimeSeries([0, 0, 0])

    _op_title, op_func = time_series_operators()["MERGE"]
    single_value_series = [op_func_wrapper(op_func, list(tsp)) for tsp in zip(*relevant_ts)]

    return TimeSeries(
        single_value_series,
        time_window=relevant_ts[0].twindow,
        conversion=_retrieve_unit_conversion_function(target_metric),
    )


def _retrieve_unit_conversion_function(metric_name: MetricName) -> Callable[[float], float]:
    if not (metric_spec := metric_info.get(metric_name)):
        return lambda v: v
    if (unit := metric_spec.get("unit")) is None:
        return lambda v: v
    return unit_info[unit].get("conversion", lambda v: v)
