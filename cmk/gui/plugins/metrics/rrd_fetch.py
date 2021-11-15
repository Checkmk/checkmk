#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Core for getting the actual raw data points via Livestatus from RRD"""

import collections
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

import livestatus

import cmk.utils.version as cmk_version
from cmk.utils.prediction import livestatus_lql, TimeSeries

import cmk.gui.plugins.metrics.timeseries as ts
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import check_metrics, reverse_translate_metric_name, RRDData
from cmk.gui.type_defs import ColumnName


def fetch_rrd_data_for_graph(graph_recipe, graph_data_range) -> RRDData:
    needed_rrd_data = get_needed_sources(graph_recipe["metrics"])

    by_service = group_needed_rrd_data_by_service(needed_rrd_data)
    rrd_data: RRDData = {}
    for (site, host_name, service_description), entries in by_service.items():
        try:
            for (perfvar, cf, scale), data in fetch_rrd_data(
                site, host_name, service_description, entries, graph_recipe, graph_data_range
            ):
                rrd_data[(site, host_name, service_description, perfvar, cf, scale)] = TimeSeries(
                    data
                )
        except livestatus.MKLivestatusNotFoundError:
            pass

    align_and_resample_rrds(rrd_data, graph_recipe["consolidation_function"])
    chop_last_empty_step(graph_data_range, rrd_data)

    return rrd_data


def align_and_resample_rrds(rrd_data: RRDData, cf):
    """RRDTool aligns start/end/step to its internal precision.

    This is returned as first 3 values in each RRD data row. Using that
    info resampling and alignment is done in reference to the first metric.

    TimeSeries are mutated in place, argument rrd_data is thus mutated"""

    start_time = None
    end_time = None
    step = None

    for spec, rrddata in rrd_data.items():
        spec_title = "%s/%s/%s" % (spec[1], spec[2], spec[3])  # host/service/perfvar
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
def chop_last_empty_step(graph_data_range, rrd_data: RRDData):
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


def needed_elements_of_expression(expression):
    if expression[0] in ["rrd", "scalar"]:
        yield tuple(expression[1:])
    elif expression[0] in ["operator", "transformation"]:
        for operand in expression[2]:
            yield from needed_elements_of_expression(operand)
    elif expression[0] == "combined" and not cmk_version.is_raw_edition():
        # Suppression is needed to silence pylint in CRE environment
        from cmk.gui.cee.plugins.metrics.graphs import (  # pylint: disable=no-name-in-module
            resolve_combined_single_metric_spec,
        )

        metrics = resolve_combined_single_metric_spec(expression[1])

        for out in (needed_elements_of_expression(m["expression"]) for m in metrics):
            yield from out


def get_needed_sources(
    metrics: List[Dict[str, Any]], condition: Callable[[Any], bool] = lambda x: True
) -> Set:
    """Extract all metric data sources definitions

    metrics: List
        List of paint-able metrics, extract from defining expression needed metrics
    condition: Callable
        Filter function for metrics that are considered"""
    return {
        source  #
        for metric in metrics
        for source in needed_elements_of_expression(metric["expression"])
        if condition(metric)
    }


def group_needed_rrd_data_by_service(needed_rrd_data):
    by_service: Dict[Tuple[str, str, str], Set[Tuple[Any, Any, Any]]] = collections.defaultdict(set)
    for site, host_name, service_description, perfvar, cf, scale in needed_rrd_data:
        by_service[(site, host_name, service_description)].add((perfvar, cf, scale))
    return by_service


def fetch_rrd_data(site, host_name, service_description, entries, graph_recipe, graph_data_range):
    start_time, end_time = graph_data_range["time_range"]

    step: Union[int, float, str] = graph_data_range["step"]
    # assumes str step is well formatted, colon separated step length & rrd point count
    if not isinstance(step, str):
        step = max(1, step)

    point_range = ":".join(map(str, (start_time, end_time, step)))
    lql_columns = list(rrd_columns(entries, graph_recipe["consolidation_function"], point_range))
    query = livestatus_lql([host_name], lql_columns, service_description)

    with sites.only_sites(site):
        return list(zip(entries, sites.live().query_row(query)))


def rrd_columns(
    metrics: List[Tuple[str, Optional[str], float]], rrd_consolidation: str, data_range: str
) -> Iterator[ColumnName]:
    """RRD data columns for each metric

    Include scaling of metric directly in query"""

    for perfvar, cf, scale in metrics:
        cf = rrd_consolidation or cf or "max"
        rpn = "%s.%s" % (perfvar, cf)
        if scale != 1.0:
            rpn += ",%f,*" % scale
        yield "rrddata:%s:%s:%s" % (perfvar, rpn, data_range)


def metric_in_all_rrd_columns(
    metric: str, rrd_consolidation: str, from_time: int, until_time: int
) -> List[ColumnName]:
    """Translate metric name to all perf_data names and construct RRD data columns for each"""

    data_range = "%s:%s:%s" % (from_time, until_time, 60)
    _metrics: List[Tuple[str, Optional[str], float]] = [
        (name, None, scale) for name, scale in reverse_translate_metric_name(metric)
    ]
    return list(rrd_columns(_metrics, rrd_consolidation, data_range))


def merge_multicol(row: Dict, rrdcols: List[ColumnName], params: Dict) -> TimeSeries:
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
