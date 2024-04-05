#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Core for getting the actual raw data points via Livestatus from RRD"""


import collections
import contextlib
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence

import livestatus
from livestatus import livestatus_lql, SiteId

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.time_series import TimeSeries, TimeSeriesValues
from cmk.gui.type_defs import ColumnName

from ._graph_specification import (
    CombinedSingleMetricSpec,
    GraphDataRange,
    GraphMetric,
    GraphRecipe,
    NeededElementForRRDDataKey,
)
from ._timeseries import op_func_wrapper, time_series_operators
from ._type_defs import GraphConsoldiationFunction, RRDData, RRDDataKey
from ._unit_info import unit_info
from ._utils import (
    CheckMetricEntry,
    find_matching_translation,
    metric_info,
    reverse_translate_into_all_potentially_relevant_metrics_cached,
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
            element.site_id,
            element.host_name,
            element.service_name,
            element.metric_name,
            element.consolidation_func_name,
            element.scale,
        )
        for metric in graph_recipe.metrics
        for element in metric.operation.needed_elements(resolve_combined_single_metric_spec)
        if isinstance(element, NeededElementForRRDDataKey)
    )
    rrd_data: RRDData = {}
    for (site, host_name, service_description), metrics in by_service.items():
        with contextlib.suppress(livestatus.MKLivestatusNotFoundError):
            for (perfvar, cf, scale), data in fetch_rrd_data(
                site,
                host_name,
                service_description,
                metrics,
                graph_recipe.consolidation_function,
                graph_data_range,
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
                else rrddata.forward_fill_resample((start_time, end_time, step))
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
    if abs(time.time() - graph_data_range.time_range[1]) > step:
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
    consolidation_func_name: GraphConsoldiationFunction | None,
    graph_data_range: GraphDataRange,
) -> list[tuple[MetricProperties, TimeSeriesValues]]:
    start_time, end_time = graph_data_range.time_range

    step = graph_data_range.step
    # assumes str step is well formatted, colon separated step length & rrd point count
    if not isinstance(step, str):
        step = max(1, step)

    point_range = ":".join(map(str, (start_time, end_time, step)))
    lql_columns = list(rrd_columns(metrics, consolidation_func_name, point_range))
    query = livestatus_lql([host_name], lql_columns, service_description)

    with sites.only_sites(site):
        return list(zip(metrics, sites.live().query_row(query)))


def rrd_columns(
    metrics: Iterable[MetricProperties],
    consolidation_func_name: GraphConsoldiationFunction | None,
    data_range: str,
) -> Iterator[ColumnName]:
    """RRD data columns for each metric

    Include scaling of metric directly in query"""

    for perfvar, cf, scale in metrics:
        cf = consolidation_func_name or cf or "max"
        rpn = f"{perfvar}.{cf}"
        if scale != 1.0:
            rpn += ",%f,*" % scale
        yield f"rrddata:{perfvar}:{rpn}:{data_range}"


def all_rrd_columns_potentially_relevant_for_metric(
    metric_name: MetricName,
    consolidation_func_name: GraphConsoldiationFunction,
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
        consolidation_func_name,
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
