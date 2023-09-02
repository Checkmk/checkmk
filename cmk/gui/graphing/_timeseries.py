#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import operator
from collections.abc import Callable, Sequence
from itertools import chain
from typing import assert_never, Literal, TypeVar

import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.prediction import TimeSeries, TimeSeriesValues

import cmk.gui.utils.escaping as escaping
from cmk.gui.i18n import _

from ._graph_specification import (
    GraphMetric,
    LineType,
    RPNExpression,
    RPNExpressionConstant,
    RPNExpressionOperator,
    RPNExpressionRRD,
    RPNExpressionTransformation,
)
from ._utils import (
    AugmentedTimeSeries,
    Curve,
    fade_color,
    parse_color,
    render_color,
    RRDData,
    time_series_expression_registry,
    TimeSeriesExpressionRegistry,
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


def compute_graph_curves(
    metrics: Sequence[GraphMetric],
    rrd_data: RRDData,
) -> list[Curve]:
    def _parse_line_type(
        mirror_prefix: Literal["", "-"], ts_line_type: LineType | Literal["ref"]
    ) -> LineType | Literal["ref"]:
        match ts_line_type:
            case "line" | "-line":
                return "line" if mirror_prefix == "" else "-line"
            case "area" | "-area":
                return "area" if mirror_prefix == "" else "-area"
            case "stack" | "-stack":
                return "stack" if mirror_prefix == "" else "-stack"
            case "ref":
                return "ref"
        assert_never((mirror_prefix, ts_line_type))

    curves = []
    for metric in metrics:
        expression = metric.expression
        time_series = evaluate_time_series_expression(expression, rrd_data)
        if not time_series:
            continue

        multi = len(time_series) > 1
        mirror_prefix: Literal["", "-"] = "-" if metric.line_type.startswith("-") else ""
        for i, ts in enumerate(time_series):
            title = metric.title
            if multi and ts.metadata.title:
                title += " - " + ts.metadata.title

            color = ts.metadata.color or metric.color
            if i % 2 == 1 and not (
                isinstance(expression, RPNExpressionTransformation)
                and expression.mode == "forecast"
            ):
                color = render_color(fade_color(parse_color(color), 0.3))

            curves.append(
                Curve(
                    {
                        "line_type": (
                            _parse_line_type(mirror_prefix, ts.metadata.line_type)
                            if multi and ts.metadata.line_type
                            else metric.line_type
                        ),
                        "color": color,
                        "title": title,
                        "rrddata": ts.data,
                    }
                )
            )

    return curves


def evaluate_time_series_expression(
    expression: RPNExpression,
    rrd_data: RRDData,
) -> Sequence[AugmentedTimeSeries]:
    try:
        expression_func = time_series_expression_registry[expression.ident]
    except KeyError:
        if cmk_version.edition() is cmk_version.Edition.CRE and expression.ident in [
            "combined",
            "transformation",
        ]:
            raise MKGeneralException(
                _(
                    "Metric transformations and combinations like Forecasts calculations, "
                    "aggregations and filtering are only available with the "
                    "Checkmk Enterprise Editions"
                )
            )

        raise MKGeneralException("Unrecognized expressions type %s" % expression.ident)

    return expression_func(expression, rrd_data)


def _expression_operator(
    expression: RPNExpression,
    rrd_data: RRDData,
) -> Sequence[AugmentedTimeSeries]:
    if not isinstance(expression, RPNExpressionOperator):
        raise TypeError(expression)

    if result := _time_series_math(
        expression.operator_name,
        [
            operand_evaluated.data
            for operand_evaluated in chain.from_iterable(
                evaluate_time_series_expression(operand, rrd_data)
                for operand in expression.operands
            )
        ],
    ):
        return [AugmentedTimeSeries(data=result)]
    return []


def _expression_rrd(
    expression: RPNExpression,
    rrd_data: RRDData,
) -> Sequence[AugmentedTimeSeries]:
    if not isinstance(expression, RPNExpressionRRD):
        raise TypeError(expression)

    if (
        key := (
            expression.site_id,
            expression.host_name,
            expression.service_name,
            expression.metric_name,
            expression.consolidation_func_name,
            expression.scale,
        )
    ) in rrd_data:
        return [AugmentedTimeSeries(data=rrd_data[key])]

    num_points, twindow = _derive_num_points_twindow(rrd_data)
    return [AugmentedTimeSeries(data=TimeSeries([None] * num_points, twindow))]


def _expression_constant(
    expression: RPNExpression,
    rrd_data: RRDData,
) -> Sequence[AugmentedTimeSeries]:
    if not isinstance(expression, RPNExpressionConstant):
        raise TypeError(expression)

    num_points, twindow = _derive_num_points_twindow(rrd_data)
    return [AugmentedTimeSeries(data=TimeSeries([expression.value] * num_points, twindow))]


def _derive_num_points_twindow(rrd_data: RRDData) -> tuple[int, tuple[int, int, int]]:
    if rrd_data:
        sample_data = next(iter(rrd_data.values()))
        return len(sample_data), sample_data.twindow
    # no data, default clean graph, use for pure scalars on custom graphs
    return 1, (0, 60, 60)


Operator = Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]


def _time_series_math(
    operator_id: Operator,
    operands_evaluated: list[TimeSeries],
) -> TimeSeries | None:
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

    return TimeSeries(
        [op_func_wrapper(op_func, list(tsp)) for tsp in zip(*operands_evaluated)], twindow
    )


_TOperatorReturn = TypeVar("_TOperatorReturn")


def op_func_wrapper(
    op_func: Callable[[TimeSeries | TimeSeriesValues], _TOperatorReturn],
    tsp: TimeSeries | TimeSeriesValues,
) -> _TOperatorReturn | None:
    if tsp.count(None) < len(tsp):  # At least one non-None value
        try:
            return op_func(tsp)
        except ZeroDivisionError:
            pass
    return None


def clean_time_series_point(tsp: TimeSeries | TimeSeriesValues) -> list[float]:
    """removes "None" entries from input list"""
    return [x for x in tsp if x is not None]


def _time_series_operator_sum(tsp: TimeSeries | TimeSeriesValues) -> float:
    return sum(clean_time_series_point(tsp))


def _time_series_operator_product(tsp: TimeSeries | TimeSeriesValues) -> float | None:
    if None in tsp:
        return None
    return functools.reduce(operator.mul, tsp, 1)


def _time_series_operator_difference(tsp: TimeSeries | TimeSeriesValues) -> float | None:
    if None in tsp:
        return None
    assert tsp[0] is not None
    assert tsp[1] is not None
    return tsp[0] - tsp[1]


def _time_series_operator_fraction(tsp: TimeSeries | TimeSeriesValues) -> float | None:
    if None in tsp or tsp[1] == 0:
        return None
    assert tsp[0] is not None
    assert tsp[1] is not None
    return tsp[0] / tsp[1]


def _time_series_operator_maximum(tsp: TimeSeries | TimeSeriesValues) -> float:
    return max(clean_time_series_point(tsp))


def _time_series_operator_minimum(tsp: TimeSeries | TimeSeriesValues) -> float:
    return min(clean_time_series_point(tsp))


def _time_series_operator_average(tsp: TimeSeries | TimeSeriesValues) -> float:
    tsp_clean = clean_time_series_point(tsp)
    return sum(tsp_clean) / len(tsp_clean)


def time_series_operators() -> (
    dict[
        Operator,
        tuple[
            str,
            Callable[[TimeSeries | TimeSeriesValues], float | None],
        ],
    ]
):
    return {
        "+": (_("Sum"), _time_series_operator_sum),
        "*": (_("Product"), _time_series_operator_product),
        "-": (_("Difference"), _time_series_operator_difference),
        "/": (_("Fraction"), _time_series_operator_fraction),
        "MAX": (_("Maximum"), _time_series_operator_maximum),
        "MIN": (_("Minimum"), _time_series_operator_minimum),
        "AVERAGE": (_("Average"), _time_series_operator_average),
        "MERGE": ("First non None", lambda x: next(iter(clean_time_series_point(x)))),
    }


def register_time_series_expressions(registy: TimeSeriesExpressionRegistry) -> None:
    registy.register_expression("operator")(_expression_operator)
    registy.register_expression("rrd")(_expression_rrd)
    registy.register_expression("constant")(_expression_constant)
