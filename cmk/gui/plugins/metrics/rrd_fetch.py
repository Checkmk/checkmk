#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Core for getting the actual raw data points via Livestatus from RRD"""

import time
import collections
from typing import List, Callable, Set  # pylint: disable=unused-import

import livestatus

from cmk.utils.prediction import livestatus_lql, TimeSeries
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
import cmk.gui.sites as sites


def fetch_rrd_data_for_graph(graph_recipe, graph_data_range):
    needed_rrd_data = get_needed_sources(graph_recipe["metrics"])

    by_service = group_needed_rrd_data_by_service(needed_rrd_data)
    rrd_data = {}
    for (site, host_name, service_description), entries in by_service.items():
        try:
            for (perfvar, cf, scale), data in \
                fetch_rrd_data(site, host_name, service_description, entries, graph_recipe, graph_data_range):
                rrd_data[(site, host_name, service_description, perfvar, cf,
                          scale)] = TimeSeries(data)
        except livestatus.MKLivestatusNotFoundError:
            pass

    start_time, end_time, step = align_and_resample_rrds(rrd_data,
                                                         graph_recipe["consolidation_function"])
    if start_time is None:  # Empty graph
        start_time, end_time = graph_data_range["time_range"]
        step = 60
    elif chop_last_empty_step(graph_data_range, step, rrd_data):
        end_time -= step

    rrd_data['__range'] = (start_time, end_time, step)
    return rrd_data


def align_and_resample_rrds(rrd_data, cf):
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

    return start_time, end_time, step


# The idea is to omit the empty last step of graphs which are showing the
# last data which ends now (at the current time) where there is not yet
# data available for the current RRD step. Showing an empty space on the
# right of the graph seems a bit odd, so strip of the last (empty) step.
#
# This makes only sense for graphs which are ending "now". So disable this
# for the other graphs.
def chop_last_empty_step(graph_data_range, step, rrd_data):
    # Disable graph chop for graphs which do not end within the current step
    if abs(time.time() - graph_data_range["time_range"][1]) > step:
        return False

    # Chop of one step from the end of the graph if that is None
    # for all curves. This is in order to avoid a gap when querying
    # up to the current time.
    for data in rrd_data.values():
        if not data or data[-1] is not None:
            return False
    for data in rrd_data.values():
        del data.values[-1]
        data.end -= step
    return True


def needed_elements_of_expression(expression):
    if expression[0] in ["rrd", "scalar"]:
        yield tuple(expression[1:])
    elif expression[0] in ["operator", "transformation"]:
        for operand in expression[2]:
            for result in needed_elements_of_expression(operand):
                yield result


def get_needed_sources(metrics, condition=lambda x: True):
    # type: (List, Callable) -> Set
    """Extract all metric data sources definitions

    metrics: List
        List of paint-able metrics, extract from defining expression needed metrics
    condition: Callable
        Filter function for metrics that are considered"""
    return set(source for metric in metrics
               for source in needed_elements_of_expression(metric["expression"])
               if condition(metric))


def group_needed_rrd_data_by_service(needed_rrd_data):
    by_service = collections.defaultdict(set)
    for site, host_name, service_description, perfvar, cf, scale in needed_rrd_data:
        by_service[(site, host_name, service_description)].add((perfvar, cf, scale))
    return by_service


def fetch_rrd_data(site, host_name, service_description, entries, graph_recipe, graph_data_range):
    start_time, end_time = graph_data_range["time_range"]

    step = graph_data_range["step"]

    point_range = ":".join(map(str, (start_time, end_time, max(1, step))))
    query = livestatus_query_for_rrd_data(host_name, service_description, entries,
                                          graph_recipe["consolidation_function"], point_range)
    with sites.only_sites(site):
        return zip(entries, sites.live().query_row(query))


def livestatus_query_for_rrd_data(host_name, service_description, metric_cols, default_cf,
                                  point_range):
    lql_columns = []
    for nr, (perfvar, cf, scale) in enumerate(metric_cols):
        if default_cf:
            cf = default_cf
        else:
            cf = cf or "max"

        rpn = "%s.%s" % (perfvar, cf)
        if scale != 1.0:
            rpn += ",%f,*" % scale
        lql_columns.append("rrddata:m%d:%s:%s" % (nr, rpn, point_range))

    return livestatus_lql([host_name], lql_columns, service_description)
