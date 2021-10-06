#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import operator
from itertools import chain
from typing import List, Literal, Optional, Sequence, Tuple

import cmk.utils.version as cmk_version
from cmk.utils.prediction import TimeSeries

import cmk.gui.utils.escaping as escaping
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import (
    ExpressionParams,
    fade_color,
    parse_color,
    render_color,
    RRDData,
    time_series_expression_registry,
)

# .
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


def compute_graph_curves(metrics, rrd_data: RRDData):
    curves = []
    for metric_definition in metrics:
        expression = metric_definition["expression"]
        time_series = evaluate_time_series_expression(expression, rrd_data)
        if not time_series:
            continue

        multi = len(time_series) > 1
        mirror_prefix = "-" if metric_definition["line_type"].startswith("-") else ""
        for i, ts in enumerate(time_series):
            title = metric_definition["title"]
            if ts.metadata.get("title") and multi:
                title += " - " + ts.metadata["title"]

            color = metric_definition.get("color", ts.metadata.get("color", "#000000"))
            if i % 2 == 1 and not (
                expression[0] == "transformation" and expression[1][0] == "forecast"
            ):
                color = render_color(fade_color(parse_color(color), 0.3))

            curves.append(
                {
                    "line_type": mirror_prefix + ts.metadata.get("line_type", "")
                    if multi
                    else metric_definition["line_type"],
                    "color": color,
                    "title": title,
                    "rrddata": ts,
                }
            )

    return curves


def evaluate_time_series_expression(expression, rrd_data: RRDData) -> Sequence[TimeSeries]:
    ident, parameters = expression[0], expression[1:]

    try:
        expression_func = time_series_expression_registry[ident]
    except KeyError:
        if cmk_version.is_raw_edition() and ident in ["combined", "transformation"]:
            raise MKGeneralException(
                _(
                    "Metric transformations and combinations like Forecasts calculations, "
                    "aggregations and filtering are only available with the "
                    "Checkmk Enterprise Editions"
                )
            )

        raise MKGeneralException("Unrecognized expressions type %s" % ident)

    return expression_func(parameters, rrd_data)


@time_series_expression_registry.register_expression("operator")
def expression_operator(parameters: ExpressionParams, rrd_data: RRDData) -> Sequence[TimeSeries]:
    operator_id, operands = parameters
    operands_evaluated = list(
        chain.from_iterable(evaluate_time_series_expression(a, rrd_data) for a in operands)
    )
    if result := time_series_math(operator_id, operands_evaluated):
        return [result]
    return []


@time_series_expression_registry.register_expression("rrd")
def expression_rrd(parameters: ExpressionParams, rrd_data: RRDData) -> Sequence[TimeSeries]:
    key = (parameters[0], parameters[1], parameters[2], parameters[3], parameters[4], parameters[5])
    if key in rrd_data:
        return [rrd_data[key]]
    num_points, twindow = _derive_num_points_twindow(rrd_data)
    return [TimeSeries([None] * num_points, twindow)]


@time_series_expression_registry.register_expression("constant")
def expression_constant(parameters: ExpressionParams, rrd_data: RRDData) -> Sequence[TimeSeries]:
    num_points, twindow = _derive_num_points_twindow(rrd_data)
    return [TimeSeries([parameters[0]] * num_points, twindow)]


def _derive_num_points_twindow(rrd_data: RRDData) -> Tuple[int, Tuple[int, int, int]]:
    if rrd_data:
        sample_data = next(iter(rrd_data.values()))
        return len(sample_data), sample_data.twindow
    # no data, default clean graph, use for pure scalars on custom graphs
    return 1, (0, 60, 60)


def time_series_math(
    operator_id: Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"],
    operands_evaluated: List[TimeSeries],
) -> Optional[TimeSeries]:
    operators = time_series_operators()
    if operator_id not in operators:
        raise MKGeneralException(
            _("Undefined operator '%s' in graph expression")
            % escaping.escape_attribute(operator_id)
        )
    # Test for correct arity on FOUND[evaluated] data
    if any(
        (
            operator_id in ["-", "/"] and len(operands_evaluated) != 2,
            len(operands_evaluated) < 1,
        )
    ):
        # raise MKGeneralException(_("Incorrect amount of data to correctly evaluate expression"))
        # Silently return so to get an empty graph slot
        return None

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
