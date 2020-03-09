#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import operator
import functools

import cmk
import cmk.gui.escaping as escaping
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics import stats

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
        if expression[0] == "transformation" and expression[1][0] == "forecast":
            curves.extend(multiline_curves(metric_definition, rrd_data))
        else:

            curves.append({
                "line_type": metric_definition["line_type"],
                "color": metric_definition["color"],
                "title": metric_definition["title"],
                "rrddata": evaluate_time_series_expression(expression, rrd_data),
            })
    return curves


def multiline_curves(metric_definition, rrd_data):
    "For the moment only works on forecast"
    time_series = evaluate_time_series_expression(metric_definition["expression"], rrd_data)
    for line, color, title, ts in time_series:
        yield {
            "line_type": line,
            'color': color,
            'title': "%s - %s" % (metric_definition["title"], title),
            'rrddata': ts
        }


def evaluate_time_series_expression(expression, rrd_data):
    if rrd_data:
        num_points = len(list(rrd_data.values())[0])
    else:
        num_points = 1

    if expression[0] == "operator":
        operator_id, operands = expression[1:]
        operands_evaluated = [evaluate_time_series_expression(a, rrd_data) for a in operands]
        return time_series_math(operator_id, operands_evaluated)

    if expression[0] == "transformation":
        (transform, conf), operands = expression[1:]
        operands_evaluated = evaluate_time_series_expression(operands[0], rrd_data)
        if transform == 'percentile':
            return time_series_operator_perc(operands_evaluated, conf)
        if transform == 'forecast':
            if cmk.is_raw_edition():
                raise MKGeneralException(
                    _("Forecast calculations are only available with the "
                      "Checkmk Enterprise Editions"))
            # Suppression is needed to silence pylint in CRE environment
            from cmk.gui.cee.plugins.metrics.forecasts import time_series_transform_forecast  # pylint: disable=no-name-in-module
            return time_series_transform_forecast(operands_evaluated, conf)

    if expression[0] == "rrd":
        key = tuple(expression[1:])
        if key in rrd_data:
            return rrd_data[key]
        return [None] * num_points

    if expression[0] == "constant":
        return [expression[1]] * num_points

    raise NotImplementedError()


def time_series_math(operator_id, operands_evaluated):
    operators = time_series_operators()
    if operator_id not in operators:
        raise MKGeneralException(
            _("Undefined operator '%s' in graph expression") %
            escaping.escape_attribute(operator_id))
    _op_title, op_func = operators[operator_id]

    return [op_func_wrapper(op_func, tsp) for tsp in zip(*operands_evaluated)]


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
    if None in tsp:
        return None
    return tsp[0] / tsp[1]


def time_series_operator_maximum(tsp):
    return max(clean_time_series_point(tsp))


def time_series_operator_minimum(tsp):
    return min(clean_time_series_point(tsp))


def time_series_operator_average(tsp):
    tsp = clean_time_series_point(tsp)
    return sum(tsp) / len(tsp)


def time_series_operator_perc(tsp, percentile):
    points = len(tsp)
    tsp = clean_time_series_point(tsp)
    perc = stats.percentile(tsp, percentile) if tsp else None
    return [perc] * points


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
