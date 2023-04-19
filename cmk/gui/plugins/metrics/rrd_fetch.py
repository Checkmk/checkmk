#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Core for getting the actual raw data points via Livestatus from RRD"""

import collections
import time
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import livestatus
from livestatus import SiteId

import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.prediction import livestatus_lql, TimeSeries, TimeSeriesValues
from cmk.utils.type_defs import HostName, ServiceName

import cmk.gui.plugins.metrics.timeseries as ts
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import (
    check_metrics,
    CombinedGraphMetricSpec,
    GraphConsoldiationFunction,
    GraphDataRange,
    GraphMetric,
    GraphRecipe,
    reverse_translate_metric_name,
    RRDData,
)
from cmk.gui.type_defs import ColumnName, CombinedGraphSpec


def fetch_rrd_data_for_graph(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    resolve_combined_single_metric_spec: Callable[
        [CombinedGraphSpec], Sequence[CombinedGraphMetricSpec]
    ],
) -> RRDData:
    needed_rrd_data = get_needed_sources(
        graph_recipe["metrics"], resolve_combined_single_metric_spec
    )

    by_service = group_needed_rrd_data_by_service(needed_rrd_data)
    rrd_data: RRDData = {}
    for (site, host_name, service_description), metrics in by_service.items():
        try:
            for (perfvar, cf, scale), data in fetch_rrd_data(
                site, host_name, service_description, metrics, graph_recipe, graph_data_range
            ):
                rrd_data[(site, host_name, service_description, perfvar, cf, scale)] = TimeSeries(
                    data
                )
        except livestatus.MKLivestatusNotFoundError:
            pass

    align_and_resample_rrds(rrd_data, graph_recipe["consolidation_function"])
    chop_last_empty_step(graph_data_range, rrd_data)

    return rrd_data


def align_and_resample_rrds(rrd_data: RRDData, cf: GraphConsoldiationFunction) -> None:
    """RRDTool aligns start/end/step to its internal precision.

    This is returned as first 3 values in each RRD data row. Using that
    info resampling and alignment is done in reference to the first metric.

    TimeSeries are mutated in place, argument rrd_data is thus mutated"""

    start_time = None
    end_time = None
    step = None

    for spec, rrddata in rrd_data.items():
        spec_title = f"{spec[1]}/{spec[2]}/{spec[3]}"  # host/service/perfvar
        if not rrddata:
            raise MKGeneralException(_("Cannot get RRD data for %s") % spec_title)

        if start_time is None:
            start_time, end_time, step = rrddata.twindow
        else:
            if (start_time, end_time, step) != rrddata.twindow:
                if step >= rrddata.twindow[2]:
                    rrddata.values = rrddata.downsample((start_time, end_time, step), spec[4] or cf)
                elif step < rrddata.twindow[2]:
                    rrddata.values = rrddata.bfill_upsample((start_time, end_time, step), 0)


# The idea is to omit the empty last step of graphs which are showing the
# last data which ends now (at the current time) where there is not yet
# data available for the current RRD step. Showing an empty space on the
# right of the graph seems a bit odd, so strip of the last (empty) step.
#
# This makes only sense for graphs which are ending "now". So disable this
# for the other graphs.
def chop_last_empty_step(graph_data_range: GraphDataRange, rrd_data: RRDData) -> None:
    if rrd_data:
        sample_data = next(iter(rrd_data.values()))
        step = sample_data.twindow[2]
        # Disable graph chop for graphs which do not end within the current step
        if abs(time.time() - graph_data_range["time_range"][1]) > step:
            return

    # Chop of one step from the end of the graph if that is None
    # for all curves. This is in order to avoid a gap when querying
    # up to the current time.
    for data in rrd_data.values():
        if not data or data[-1] is not None:
            return

    for data in rrd_data.values():
        del data.values[-1]
        data.end -= step


def needed_elements_of_expression(  # type:ignore[no-untyped-def]
    expression,
    resolve_combined_single_metric_spec: Callable[
        [CombinedGraphSpec], Sequence[CombinedGraphMetricSpec]
    ],
):
    if expression[0] in ["rrd", "scalar"]:
        yield tuple(expression[1:])
    elif expression[0] in ["operator", "transformation"]:
        for operand in expression[2]:
            yield from needed_elements_of_expression(operand, resolve_combined_single_metric_spec)
    elif expression[0] == "combined" and not cmk_version.is_raw_edition():
        metrics = resolve_combined_single_metric_spec(expression[1])

        for out in (
            needed_elements_of_expression(m["expression"], resolve_combined_single_metric_spec)
            for m in metrics
        ):
            yield from out


def get_needed_sources(
    metrics: list[GraphMetric],
    resolve_combined_single_metric_spec: Callable[
        [CombinedGraphSpec], Sequence[CombinedGraphMetricSpec]
    ],
    *,
    condition: Callable[[Any], bool] = lambda x: True,
) -> set:
    """Extract all metric data sources definitions

    metrics: List
        List of paint-able metrics, extract from defining expression needed metrics
    condition: Callable
        Filter function for metrics that are considered"""
    return {
        source  #
        for metric in metrics
        for source in needed_elements_of_expression(
            metric["expression"],
            resolve_combined_single_metric_spec,
        )
        if condition(metric)
    }


NeededRRDData = set[
    tuple[SiteId, HostName, ServiceName, str, GraphConsoldiationFunction | None, float]
]
MetricProperties = tuple[str, GraphConsoldiationFunction | None, float]


def group_needed_rrd_data_by_service(
    needed_rrd_data: NeededRRDData,
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
    lql_columns = list(rrd_columns(metrics, graph_recipe["consolidation_function"], point_range))
    query = livestatus_lql([host_name], lql_columns, service_description)

    with sites.only_sites(site):
        return list(zip(metrics, sites.live().query_row(query)))


def rrd_columns(
    metrics: set[MetricProperties],
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


def metric_in_all_rrd_columns(
    metric: str,
    rrd_consolidation: GraphConsoldiationFunction,
    from_time: int,
    until_time: int,
) -> list[ColumnName]:
    """Translate metric name to all perf_data names and construct RRD data columns for each"""

    data_range = f"{from_time}:{until_time}:{60}"
    metrics: set[MetricProperties] = {
        (name, None, scale) for name, scale in reverse_translate_metric_name(metric)
    }
    return list(rrd_columns(metrics, rrd_consolidation, data_range))


def merge_multicol(
    row: dict[str, Any], rrdcols: list[ColumnName], params: dict[str, Any]
) -> TimeSeries:
    """Establish single timeseries for desired metric

    If Livestatus query is performed in bulk, over all possible named
    metrics that translate to desired one, it results in many empty columns
    per row. Yet, non-empty values have 3 options:

    1. Correspond to desired metric
    2. Correspond to old metric that translates into desired metric
    3. Name collision: Metric of different service translates to desired
    metric, yet same metric exist too in current service

    Thus filter first case 3, then pick both cases 1 & 2.  Finalize by merging
    the at most remaining 2 timeseries into a single one.
    """

    relevant_ts = []
    desired_metric = params["metric"]
    check_command = row["service_check_command"]
    translations = check_metrics.get(check_command, {})

    for rrdcol in rrdcols:
        if not rrdcol.startswith("rrddata"):
            continue

        if row[rrdcol] is None:
            raise MKGeneralException(_("Cannot retrieve historic data with Nagios core"))

        current_metric = rrdcol.split(":")[1]

        if translations.get(current_metric, {}).get("name", desired_metric) == desired_metric:
            if len(row[rrdcol]) > 3:
                relevant_ts.append(row[rrdcol])

    if not relevant_ts:
        return TimeSeries([0, 0, 0])

    _op_title, op_func = ts.time_series_operators()["MERGE"]
    single_value_series = [ts.op_func_wrapper(op_func, tsp) for tsp in zip(*relevant_ts)]

    return TimeSeries(single_value_series)
