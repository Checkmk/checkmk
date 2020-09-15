#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import operator
import functools

from cmk.utils.prediction import TimeSeries
import cmk.utils.version as cmk_version
import cmk.gui.escaping as escaping
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.i18n import _

if cmk_version.is_raw_edition():

    def evaluate_timeseries_transformation(transform, conf, operands_evaluated):
        raise MKGeneralException(
            _("Metric transformations and combinations like Forecasts calculations, "
              "aggregations and filtering are only available with the "
              "Checkmk Enterprise Editions"))

    def resolve_combined_single_metric_spec(expression):
        return evaluate_timeseries_transformation(None, None, None)
else:
    # Suppression is needed to silence pylint in CRE environment
    from cmk.gui.cee.plugins.metrics.timeseries import evaluate_timeseries_transformation  # pylint: disable=no-name-in-module
    from cmk.gui.cee.plugins.metrics.graphs import resolve_combined_single_metric_spec  # pylint: disable=no-name-in-module

#.
#   .--Curves--------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|   _ _ ____   _____  ___                     |
#   |                  | |  | | | | '__\ \ / / _ \/ __|                    |
#   |                  | |__| |_| | |   \ V /  __/\__ \                    |
#   |                   \____\__,_|_|    \_/ \___||___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Compute the curves from the raw RRD data by evaluating expressions. |
#   '----------------------------------------------------------------------'


def compute_graph_curves(metrics, rrd_data):
    curves = []
    for metric_definition in metrics:
        expression = metric_definition["expression"]
        time_series = evaluate_time_series_expression(expression, rrd_data)
        if not time_series:
            continue

        if len(time_series) == 1 and isinstance(time_series[0], tuple):
            time_series = time_series[0][3]

        if isinstance(time_series[0], tuple):
            for line, color, title, ts in time_series:
                curves.append({
                    "line_type": line,
                    'color': color,
                    'title': "%s - %s" % (metric_definition["title"], title),
                    'rrddata': ts
                })
        else:
            curves.append({
                "line_type": metric_definition["line_type"],
                "color": metric_definition["color"],
                "title": metric_definition["title"],
                "rrddata": time_series,
            })

    return curves


def evaluate_time_series_expression(expression, rrd_data):
    if rrd_data:
        sample_data = next(iter(rrd_data.values()))
        num_points = len(sample_data)
        twindow = sample_data.twindow
    else:
        # no data, default clean graph, use for pure scalars on custom graphs
        num_points = 1
        twindow = (0, 60, 60)

    if expression[0] == "operator":
        operator_id, operands = expression[1:]
        operands_evaluated = [evaluate_time_series_expression(a, rrd_data) for a in operands]
        return time_series_math(operator_id, operands_evaluated)

    if expression[0] == "transformation":
        (transform, conf), operands = expression[1:]
        operands_evaluated = evaluate_time_series_expression(operands[0], rrd_data)
        return evaluate_timeseries_transformation(transform, conf, operands_evaluated)

    if expression[0] == "rrd":
        key = tuple(expression[1:])
        if key in rrd_data:
            return rrd_data[key]
        return TimeSeries([None] * num_points, twindow)

    if expression[0] == "constant":
        return TimeSeries([expression[1]] * num_points, twindow)

    if expression[0] == "combined":
        metrics = resolve_combined_single_metric_spec(expression[1])

        return [(m["line_type"], m["color"], m['title'],
                 evaluate_time_series_expression(m['expression'], rrd_data)) for m in metrics]

    raise NotImplementedError()


def time_series_math(operator_id, operands_evaluated) -> TimeSeries:
    operators = time_series_operators()
    if operator_id not in operators:
        raise MKGeneralException(
            _("Undefined operator '%s' in graph expression") %
            escaping.escape_attribute(operator_id))
    _op_title, op_func = operators[operator_id]
    twindow = operands_evaluated[0].twindow

    return TimeSeries([op_func_wrapper(op_func, tsp) for tsp in zip(*operands_evaluated)], twindow)


def op_func_wrapper(op_func, tsp):
    if tsp.count(None) < len(tsp):  # At least one non-None value
        try:
            return op_func(tsp)
        except ZeroDivisionError:
            pass
    return None


def clean_time_series_point(tsp):
    """removes "None" entries from input list"""
    return [x for x in tsp if x is not None]


def time_series_operator_sum(tsp):
    return sum(clean_time_series_point(tsp))


def time_series_operator_product(tsp):
    if None in tsp:
        return None
    return functools.reduce(operator.mul, tsp, 1)


def time_series_operator_difference(tsp):
    if None in tsp:
        return None
    return tsp[0] - tsp[1]


def time_series_operator_fraction(tsp):
    if None in tsp or tsp[1] == 0:
        return None
    return tsp[0] / tsp[1]


def time_series_operator_maximum(tsp):
    return max(clean_time_series_point(tsp))


def time_series_operator_minimum(tsp):
    return min(clean_time_series_point(tsp))


def time_series_operator_average(tsp):
    tsp = clean_time_series_point(tsp)
    return sum(tsp) / len(tsp)


def time_series_operators():
    return {
        "+": (_("Sum"), time_series_operator_sum),
        "*": (_("Product"), time_series_operator_product),
        "-": (_("Difference"), time_series_operator_difference),
        "/": (_("Fraction"), time_series_operator_fraction),
        "MAX": (_("Maximum"), time_series_operator_maximum),
        "MIN": (_("Minimum"), time_series_operator_minimum),
        "AVERAGE": (_("Average"), time_series_operator_average),
        "MERGE": ("First non None", lambda x: next(iter(clean_time_series_point(x)))),
    }
