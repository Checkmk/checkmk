#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import assert_never

from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v2_unstable import metrics as metrics_v2_api

from ._objects import (
    AutoPrecision,
    Bidirectional,
    Bound,
    Constant,
    CriticalOf,
    DecimalNotation,
    Difference,
    EngineeringScientificNotation,
    Fraction,
    Graph,
    IECNotation,
    LowerCriticalOf,
    LowerWarningOf,
    MaximumOf,
    MetricName,
    MinimalRange,
    MinimumOf,
    Notation,
    Precision,
    Product,
    Quantity,
    SINotation,
    StackGroup,
    StandardScientificNotation,
    StrictPrecision,
    Sum,
    TimeNotation,
    Unit,
    WarningOf,
)

type _ApiQuantity = (
    str
    | metrics_api.Constant
    | metrics_api.WarningOf
    | metrics_api.CriticalOf
    | metrics_api.MinimumOf
    | metrics_api.MaximumOf
    | metrics_api.Sum
    | metrics_api.Product
    | metrics_api.Difference
    | metrics_api.Fraction
)

_COLORS: dict[metrics_api.Color, str] = {
    metrics_api.Color.LIGHT_RED: "#f37c7c",
    metrics_api.Color.RED: "#ed3b3b",
    metrics_api.Color.DARK_RED: "#a82a2a",
    metrics_api.Color.LIGHT_ORANGE: "#ffad54",
    metrics_api.Color.ORANGE: "#ff8400",
    metrics_api.Color.DARK_ORANGE: "#b55e00",
    metrics_api.Color.LIGHT_YELLOW: "#ffe456",
    metrics_api.Color.YELLOW: "#ffd703",
    metrics_api.Color.DARK_YELLOW: "#ac7c02",
    metrics_api.Color.LIGHT_GREEN: "#62e0bf",
    metrics_api.Color.GREEN: "#15d1a0",
    metrics_api.Color.DARK_GREEN: "#0f9472",
    metrics_api.Color.LIGHT_BLUE: "#6fc1f7",
    metrics_api.Color.BLUE: "#28a2f3",
    metrics_api.Color.DARK_BLUE: "#1c73ad",
    metrics_api.Color.LIGHT_CYAN: "#68eeee",
    metrics_api.Color.CYAN: "#1ee6e6",
    metrics_api.Color.DARK_CYAN: "#17b5b5",
    metrics_api.Color.LIGHT_PURPLE: "#acaaff",
    metrics_api.Color.PURPLE: "#8380ff",
    metrics_api.Color.DARK_PURPLE: "#5d5bb5",
    metrics_api.Color.LIGHT_PINK: "#f9a8e2",
    metrics_api.Color.PINK: "#ec48b6",
    metrics_api.Color.DARK_PINK: "#be187a",
    metrics_api.Color.LIGHT_BROWN: "#d4ad84",
    metrics_api.Color.BROWN: "#bf8548",
    metrics_api.Color.DARK_BROWN: "#885e33",
    metrics_api.Color.LIGHT_GRAY: "#acacac",
    metrics_api.Color.GRAY: "#8c8c8c",
    metrics_api.Color.DARK_GRAY: "#5d5d5d",
    metrics_api.Color.BLACK: "#1e262e",
    metrics_api.Color.WHITE: "#ffffff",
}


def _parse_color(color: metrics_api.Color) -> str:
    return _COLORS[color]


def _parse_unit(unit: metrics_api.Unit) -> Unit:
    notation: Notation
    match unit.notation:
        case metrics_api.DecimalNotation(symbol):
            notation = DecimalNotation(symbol)
        case metrics_api.SINotation(symbol):
            notation = SINotation(symbol)
        case metrics_api.IECNotation(symbol):
            notation = IECNotation(symbol)
        case metrics_api.StandardScientificNotation(symbol):
            notation = StandardScientificNotation(symbol)
        case metrics_api.EngineeringScientificNotation(symbol):
            notation = EngineeringScientificNotation(symbol)
        case metrics_api.TimeNotation():
            notation = TimeNotation()
        case _:
            assert_never(unit.notation)

    precision: Precision
    match unit.precision:
        case metrics_api.AutoPrecision(digits):
            precision = AutoPrecision(digits)
        case metrics_api.StrictPrecision(digits):
            precision = StrictPrecision(digits)
        case _:
            assert_never(unit.precision)

    return Unit(notation=notation, precision=precision)


def _parse_quantity(
    quantity: _ApiQuantity,
    localizer: Callable[[str], str],
) -> Quantity:
    match quantity:
        case str():
            return MetricName(quantity)
        case metrics_api.Constant():
            return Constant(
                title=quantity.title.localize(localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
                value=quantity.value,
            )
        case metrics_v2_api.LowerWarningOf():
            return LowerWarningOf(metric_name=MetricName(quantity.metric_name))
        case metrics_v2_api.LowerCriticalOf():
            return LowerCriticalOf(metric_name=MetricName(quantity.metric_name))
        case metrics_api.WarningOf():
            return WarningOf(metric_name=MetricName(quantity.metric_name))
        case metrics_api.CriticalOf():
            return CriticalOf(metric_name=MetricName(quantity.metric_name))
        case metrics_api.MinimumOf():
            return MinimumOf(
                metric_name=MetricName(quantity.metric_name),
                color=_parse_color(quantity.color),
            )
        case metrics_api.MaximumOf():
            return MaximumOf(
                metric_name=MetricName(quantity.metric_name),
                color=_parse_color(quantity.color),
            )
        case metrics_api.Sum():
            return Sum(
                title=quantity.title.localize(localizer),
                color=_parse_color(quantity.color),
                summands=[_parse_quantity(s, localizer) for s in quantity.summands],
            )
        case metrics_api.Product():
            return Product(
                title=quantity.title.localize(localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
                factors=[_parse_quantity(f, localizer) for f in quantity.factors],
            )
        case metrics_api.Difference():
            return Difference(
                title=quantity.title.localize(localizer),
                color=_parse_color(quantity.color),
                minuend=_parse_quantity(quantity.minuend, localizer),
                subtrahend=_parse_quantity(quantity.subtrahend, localizer),
            )
        case metrics_api.Fraction():
            return Fraction(
                title=quantity.title.localize(localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
                dividend=_parse_quantity(quantity.dividend, localizer),
                divisor=_parse_quantity(quantity.divisor, localizer),
            )
        case _:
            assert_never(quantity)


def _parse_bound(
    bound: int | float | _ApiQuantity,
    localizer: Callable[[str], str],
) -> Bound:
    if isinstance(bound, int | float):
        return bound
    return _parse_quantity(bound, localizer)


def _parse_minimal_range(
    minimal_range: graphs_api.MinimalRange,
    localizer: Callable[[str], str],
) -> MinimalRange:
    return MinimalRange(
        lower=_parse_bound(minimal_range.lower, localizer),
        upper=_parse_bound(minimal_range.upper, localizer),
    )


def _parse_graph(graph: graphs_api.Graph, localizer: Callable[[str], str]) -> Graph:
    return Graph(
        name=graph.name,
        title=graph.title.localize(localizer),
        vertical_range=(
            None
            if graph.minimal_range is None
            else _parse_minimal_range(graph.minimal_range, localizer)
        ),
        stack_groups=(
            [StackGroup(members=[_parse_quantity(q, localizer) for q in graph.compound_lines])]
            if graph.compound_lines
            else []
        ),
        simple_lines=[_parse_quantity(q, localizer) for q in graph.simple_lines],
        optional=[MetricName(name) for name in graph.optional],
        conflicting=[MetricName(name) for name in graph.conflicting],
    )


def parse_graph_from_api(
    graph: graphs_api.Graph | graphs_api.Bidirectional,
    localizer: Callable[[str], str],
) -> Graph | Bidirectional:
    match graph:
        case graphs_api.Graph():
            return _parse_graph(graph, localizer)
        case graphs_api.Bidirectional():
            return Bidirectional(
                name=graph.name,
                title=graph.title.localize(localizer),
                lower=_parse_graph(graph.lower, localizer),
                upper=_parse_graph(graph.upper, localizer),
            )
        case _:
            assert_never(graph)
