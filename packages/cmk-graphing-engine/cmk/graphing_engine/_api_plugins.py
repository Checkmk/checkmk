#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import assert_never

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable

from ._naming import MetricName

type ApiQuantity = (
    str
    | metrics_v1.Constant
    | metrics_v1.WarningOf
    | metrics_v1.CriticalOf
    | metrics_v2_unstable.LowerWarningOf
    | metrics_v2_unstable.LowerCriticalOf
    | metrics_v1.MinimumOf
    | metrics_v1.MaximumOf
    | metrics_v1.Sum
    | metrics_v1.Product
    | metrics_v1.Difference
    | metrics_v1.Fraction
)

type ApiScalar = (
    metrics_v1.WarningOf
    | metrics_v1.CriticalOf
    | metrics_v2_unstable.LowerWarningOf
    | metrics_v2_unstable.LowerCriticalOf
    | metrics_v1.MinimumOf
    | metrics_v1.MaximumOf
)


def operands_of(quantity: ApiQuantity) -> Sequence[ApiQuantity]:
    match quantity:
        case metrics_v1.Sum():
            return quantity.summands
        case metrics_v1.Product():
            return quantity.factors
        case metrics_v1.Difference():
            return [quantity.minuend, quantity.subtrahend]
        case metrics_v1.Fraction():
            return [quantity.dividend, quantity.divisor]
        case _:
            return []


def is_scalar(quantity: ApiQuantity) -> bool:
    match quantity:
        case str():
            return False
        case (
            metrics_v1.Constant()
            | metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            return True
        case (
            metrics_v1.Sum()
            | metrics_v1.Product()
            | metrics_v1.Difference()
            | metrics_v1.Fraction()
        ):
            return all(is_scalar(operand) for operand in operands_of(quantity))
        case _:
            assert_never(quantity)


def metric_names_in_quantity(quantity: ApiQuantity) -> Iterable[MetricName]:
    match quantity:
        case str():
            yield MetricName(quantity)
        case metrics_v1.Constant():
            return
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            yield MetricName(quantity.metric_name)
        case (
            metrics_v1.Sum()
            | metrics_v1.Product()
            | metrics_v1.Difference()
            | metrics_v1.Fraction()
        ):
            for operand in operands_of(quantity):
                yield from metric_names_in_quantity(operand)
        case _:
            assert_never(quantity)


def drawn_metric_names_of_graph(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
) -> Sequence[MetricName]:
    return list(
        dict.fromkeys(
            name
            for quantity in (*graph.compound_lines, *graph.simple_lines)
            if not is_scalar(quantity)
            for name in metric_names_in_quantity(quantity)
        )
    )
