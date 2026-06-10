#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable

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
    metric_names_in_title,
    MetricName,
    MinimalRange,
    MinimumOf,
    Notation,
    Precision,
    Product,
    Quantity,
    RRDMetric,
    SINotation,
    StackGroup,
    StandardScientificNotation,
    StrictPrecision,
    Sum,
    TimeNotation,
    Unit,
    WarningOf,
)
from ._options import ServiceRef

type _ApiQuantity = (
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

_COLORS: dict[metrics_v1.Color, str] = {
    metrics_v1.Color.LIGHT_RED: "#f37c7c",
    metrics_v1.Color.RED: "#ed3b3b",
    metrics_v1.Color.DARK_RED: "#a82a2a",
    metrics_v1.Color.LIGHT_ORANGE: "#ffad54",
    metrics_v1.Color.ORANGE: "#ff8400",
    metrics_v1.Color.DARK_ORANGE: "#b55e00",
    metrics_v1.Color.LIGHT_YELLOW: "#ffe456",
    metrics_v1.Color.YELLOW: "#ffd703",
    metrics_v1.Color.DARK_YELLOW: "#ac7c02",
    metrics_v1.Color.LIGHT_GREEN: "#62e0bf",
    metrics_v1.Color.GREEN: "#15d1a0",
    metrics_v1.Color.DARK_GREEN: "#0f9472",
    metrics_v1.Color.LIGHT_BLUE: "#6fc1f7",
    metrics_v1.Color.BLUE: "#28a2f3",
    metrics_v1.Color.DARK_BLUE: "#1c73ad",
    metrics_v1.Color.LIGHT_CYAN: "#68eeee",
    metrics_v1.Color.CYAN: "#1ee6e6",
    metrics_v1.Color.DARK_CYAN: "#17b5b5",
    metrics_v1.Color.LIGHT_PURPLE: "#acaaff",
    metrics_v1.Color.PURPLE: "#8380ff",
    metrics_v1.Color.DARK_PURPLE: "#5d5bb5",
    metrics_v1.Color.LIGHT_PINK: "#f9a8e2",
    metrics_v1.Color.PINK: "#ec48b6",
    metrics_v1.Color.DARK_PINK: "#be187a",
    metrics_v1.Color.LIGHT_BROWN: "#d4ad84",
    metrics_v1.Color.BROWN: "#bf8548",
    metrics_v1.Color.DARK_BROWN: "#885e33",
    metrics_v1.Color.LIGHT_GRAY: "#acacac",
    metrics_v1.Color.GRAY: "#8c8c8c",
    metrics_v1.Color.DARK_GRAY: "#5d5d5d",
    metrics_v1.Color.BLACK: "#1e262e",
    metrics_v1.Color.WHITE: "#ffffff",
}


def _parse_color(color: metrics_v1.Color) -> str:
    return _COLORS[color]


def _parse_unit(unit: metrics_v1.Unit) -> Unit:
    notation: Notation
    match unit.notation:
        case metrics_v1.DecimalNotation(symbol):
            notation = DecimalNotation(symbol)
        case metrics_v1.SINotation(symbol):
            notation = SINotation(symbol)
        case metrics_v1.IECNotation(symbol):
            notation = IECNotation(symbol)
        case metrics_v1.StandardScientificNotation(symbol):
            notation = StandardScientificNotation(symbol)
        case metrics_v1.EngineeringScientificNotation(symbol):
            notation = EngineeringScientificNotation(symbol)
        case metrics_v1.TimeNotation():
            notation = TimeNotation()
        case _:
            assert_never(unit.notation)

    precision: Precision
    match unit.precision:
        case metrics_v1.AutoPrecision(digits):
            precision = AutoPrecision(digits)
        case metrics_v1.StrictPrecision(digits):
            precision = StrictPrecision(digits)
        case _:
            assert_never(unit.precision)

    return Unit(notation=notation, precision=precision)


# Defaults for metrics that have no registered definition.
_FALLBACK_COLOR = _COLORS[metrics_v1.Color.GRAY]


@dataclass(frozen=True)
class _ParseContext:
    localizer: Callable[[str], str]
    service: ServiceRef
    metrics: Mapping[str, metrics_v1.Metric]

    def rrd_metric(self, metric_name: str) -> RRDMetric:
        # Discovery leaves the consolidation function open; the graph request supplies it at fetch.
        return RRDMetric(
            host_name=self.service.host_name,
            service_name=self.service.service_name,
            metric_name=MetricName(metric_name),
        )

    def metric_color(self, metric_name: str) -> str:
        if (definition := self.metrics.get(metric_name)) is None:
            return _FALLBACK_COLOR
        return _parse_color(definition.color)


def _parse_quantity(quantity: _ApiQuantity, context: _ParseContext) -> Quantity:
    match quantity:
        case str():
            return context.rrd_metric(quantity)
        case metrics_v1.Constant():
            return Constant(
                title=quantity.title.localize(context.localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
                value=quantity.value,
            )
        case metrics_v2_unstable.LowerWarningOf():
            return LowerWarningOf(
                metric=context.rrd_metric(quantity.metric_name),
                color=context.metric_color(quantity.metric_name),
            )
        case metrics_v2_unstable.LowerCriticalOf():
            return LowerCriticalOf(
                metric=context.rrd_metric(quantity.metric_name),
                color=context.metric_color(quantity.metric_name),
            )
        case metrics_v1.WarningOf():
            return WarningOf(
                metric=context.rrd_metric(quantity.metric_name),
                color=context.metric_color(quantity.metric_name),
            )
        case metrics_v1.CriticalOf():
            return CriticalOf(
                metric=context.rrd_metric(quantity.metric_name),
                color=context.metric_color(quantity.metric_name),
            )
        case metrics_v1.MinimumOf():
            return MinimumOf(
                metric=context.rrd_metric(quantity.metric_name),
                color=_parse_color(quantity.color),
            )
        case metrics_v1.MaximumOf():
            return MaximumOf(
                metric=context.rrd_metric(quantity.metric_name),
                color=_parse_color(quantity.color),
            )
        case metrics_v1.Sum():
            return Sum(
                title=quantity.title.localize(context.localizer),
                color=_parse_color(quantity.color),
                summands=[_parse_quantity(s, context) for s in quantity.summands],
            )
        case metrics_v1.Product():
            return Product(
                title=quantity.title.localize(context.localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
                factors=[_parse_quantity(f, context) for f in quantity.factors],
            )
        case metrics_v1.Difference():
            return Difference(
                title=quantity.title.localize(context.localizer),
                color=_parse_color(quantity.color),
                minuend=_parse_quantity(quantity.minuend, context),
                subtrahend=_parse_quantity(quantity.subtrahend, context),
            )
        case metrics_v1.Fraction():
            return Fraction(
                title=quantity.title.localize(context.localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
                dividend=_parse_quantity(quantity.dividend, context),
                divisor=_parse_quantity(quantity.divisor, context),
            )
        case _:
            assert_never(quantity)


def _metric_names_in_quantity(quantity: _ApiQuantity) -> Iterable[MetricName]:
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
        case metrics_v1.Sum():
            for summand in quantity.summands:
                yield from _metric_names_in_quantity(summand)
        case metrics_v1.Product():
            for factor in quantity.factors:
                yield from _metric_names_in_quantity(factor)
        case metrics_v1.Difference():
            yield from _metric_names_in_quantity(quantity.minuend)
            yield from _metric_names_in_quantity(quantity.subtrahend)
        case metrics_v1.Fraction():
            yield from _metric_names_in_quantity(quantity.dividend)
            yield from _metric_names_in_quantity(quantity.divisor)
        case _:
            assert_never(quantity)


def metric_names_of_title(title: Title) -> Sequence[MetricName]:
    # Metric names referenced by title expressions are independent of the localization, so the
    # title is rendered without translating it.
    return list(metric_names_in_title(title.localize(lambda text: text)))


def metric_names_of_graph(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
) -> Sequence[MetricName]:
    return list(
        set(
            name
            for quantity in (*graph.compound_lines, *graph.simple_lines)
            for name in _metric_names_in_quantity(quantity)
        )
        | set(metric_names_of_title(graph.title))
    )


def _parse_bound(bound: int | float | _ApiQuantity, context: _ParseContext) -> Bound:
    if isinstance(bound, int | float):
        return bound
    return _parse_quantity(bound, context)


def _parse_minimal_range(
    minimal_range: graphs_v1.MinimalRange | graphs_v2_unstable.MinimalRange,
    context: _ParseContext,
) -> MinimalRange:
    return MinimalRange(
        lower=_parse_bound(minimal_range.lower, context),
        upper=_parse_bound(minimal_range.upper, context),
    )


def _parse_graph(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    context: _ParseContext,
) -> Graph:
    return Graph(
        name=graph.name,
        title=graph.title.localize(context.localizer),
        vertical_range=(
            None
            if graph.minimal_range is None
            else _parse_minimal_range(graph.minimal_range, context)
        ),
        stack_groups=(
            [StackGroup(members=[_parse_quantity(q, context) for q in graph.compound_lines])]
            if graph.compound_lines
            else []
        ),
        simple_lines=[_parse_quantity(q, context) for q in graph.simple_lines],
    )


def parse_graph_from_api(
    graph: (
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ),
    localizer: Callable[[str], str],
    service: ServiceRef,
    metrics: Mapping[str, metrics_v1.Metric],
) -> Graph | Bidirectional:
    context = _ParseContext(
        localizer=localizer,
        service=service,
        metrics=metrics,
    )
    match graph:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            return _parse_graph(graph, context)
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            return Bidirectional(
                name=graph.name,
                title=graph.title.localize(localizer),
                lower=_parse_graph(graph.lower, context),
                upper=_parse_graph(graph.upper, context),
            )
        case _:
            assert_never(graph)
