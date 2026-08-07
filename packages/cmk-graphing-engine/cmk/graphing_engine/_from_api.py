#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, Protocol

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable

from ._display import (
    FALLBACK_ATTRIBUTES,
    metric_display_attributes,
    parse_color,
    parse_unit,
)
from ._graph import Bound, Curve, Graph, Line, MinimalRange, Rule, Stack
from ._naming import MetricName, Service
from ._quantities import (
    Constant,
    Difference,
    Fraction,
    Product,
    QuantityProtocol,
    rrd_metric_of,
    RRDMetric,
    ScalarKind,
    ScalarOf,
    Sum,
)
from ._units import CurveAttributes

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


class QuantityBuilderProtocol(Protocol):
    def __call__(self, metrics: Sequence[RRDMetric]) -> QuantityProtocol: ...


def build_single_quantity(metrics: Sequence[RRDMetric]) -> QuantityProtocol:
    (metric,) = metrics
    return metric


def drawn_quantity(
    metric_name: str,
    services: Sequence[Service],
    quantity_builder: QuantityBuilderProtocol,
) -> QuantityProtocol:
    return quantity_builder([rrd_metric_of(service, metric_name) for service in services])


@dataclass(frozen=True)
class _ParseContext:
    services: Sequence[Service]
    quantity_builder: QuantityBuilderProtocol
    localizer: Callable[[str], str]
    registered_metrics: Mapping[str, metrics_v1.Metric]

    def drawn(self, metric_name: str) -> QuantityProtocol:
        return drawn_quantity(metric_name, self.services, self.quantity_builder)

    def scalar(self, metric_name: str) -> RRDMetric:
        return rrd_metric_of(self.services[0], metric_name)


def _operands_of(quantity: _ApiQuantity) -> Sequence[_ApiQuantity]:
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


def _curve_display(quantity: _ApiQuantity, context: _ParseContext) -> CurveAttributes:
    match quantity:
        case str():
            return metric_display_attributes(
                quantity, context.localizer, context.registered_metrics
            )
        case metrics_v1.Constant():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=parse_unit(quantity.unit),
                color=parse_color(quantity.color),
            )
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
        ):
            return _curve_display(quantity.metric_name, context)
        case metrics_v1.MinimumOf() | metrics_v1.MaximumOf():
            attributes = _curve_display(quantity.metric_name, context)
            return CurveAttributes(
                title=attributes.title, unit=attributes.unit, color=parse_color(quantity.color)
            )
        case metrics_v1.Sum() | metrics_v1.Difference():
            # A sum and a difference are in the unit of what they add up or take apart, so the API
            # does not spell one out: it is the first operand's.
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=_curve_display(_operands_of(quantity)[0], context).unit,
                color=parse_color(quantity.color),
            )
        case metrics_v1.Product() | metrics_v1.Fraction():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=parse_unit(quantity.unit),
                color=parse_color(quantity.color),
            )
        case _:
            assert_never(quantity)


def _parse_quantity(quantity: _ApiQuantity, context: _ParseContext) -> QuantityProtocol:
    match quantity:
        case str():
            return context.drawn(quantity)
        case metrics_v1.Constant():
            return Constant(quantity.value, display=_curve_display(quantity, context))
        case metrics_v2_unstable.LowerWarningOf():
            return ScalarOf(
                metric=context.scalar(quantity.metric_name),
                scalar_kind=ScalarKind.LOWER_WARNING,
            )
        case metrics_v2_unstable.LowerCriticalOf():
            return ScalarOf(
                metric=context.scalar(quantity.metric_name),
                scalar_kind=ScalarKind.LOWER_CRITICAL,
            )
        case metrics_v1.WarningOf():
            return ScalarOf(
                metric=context.scalar(quantity.metric_name), scalar_kind=ScalarKind.WARNING
            )
        case metrics_v1.CriticalOf():
            return ScalarOf(
                metric=context.scalar(quantity.metric_name), scalar_kind=ScalarKind.CRITICAL
            )
        case metrics_v1.MinimumOf():
            return ScalarOf(
                metric=context.scalar(quantity.metric_name),
                scalar_kind=ScalarKind.MINIMUM,
                color=parse_color(quantity.color),
            )
        case metrics_v1.MaximumOf():
            return ScalarOf(
                metric=context.scalar(quantity.metric_name),
                scalar_kind=ScalarKind.MAXIMUM,
                color=parse_color(quantity.color),
            )
        case metrics_v1.Sum():
            return Sum(
                summands=[_parse_quantity(s, context) for s in quantity.summands],
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Product():
            return Product(
                factors=[_parse_quantity(f, context) for f in quantity.factors],
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Difference():
            return Difference(
                minuend=_parse_quantity(quantity.minuend, context),
                subtrahend=_parse_quantity(quantity.subtrahend, context),
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Fraction():
            return Fraction(
                dividend=_parse_quantity(quantity.dividend, context),
                divisor=_parse_quantity(quantity.divisor, context),
                display=_curve_display(quantity, context),
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
        case (
            metrics_v1.Sum()
            | metrics_v1.Product()
            | metrics_v1.Difference()
            | metrics_v1.Fraction()
        ):
            for operand in _operands_of(quantity):
                yield from _metric_names_in_quantity(operand)
        case _:
            assert_never(quantity)


def _is_scalar(quantity: _ApiQuantity) -> bool:
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
            return all(_is_scalar(operand) for operand in _operands_of(quantity))
        case _:
            assert_never(quantity)


def drawn_metric_names_of_graph(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
) -> Sequence[MetricName]:
    return list(
        {
            name
            for quantity in (*graph.compound_lines, *graph.simple_lines)
            if not _is_scalar(quantity)
            for name in _metric_names_in_quantity(quantity)
        }
    )


def _parse_bound(bound: int | float | _ApiQuantity, context: _ParseContext) -> Bound:
    if isinstance(bound, int | float):
        return bound
    return _parse_quantity(bound, context)


def _parse_range(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    context: _ParseContext,
) -> MinimalRange | None:
    if graph.minimal_range is None:
        return None
    return MinimalRange(
        lower=_parse_bound(graph.minimal_range.lower, context),
        upper=_parse_bound(graph.minimal_range.upper, context),
    )


def _widest_bound(
    of_upper: Bound | None,
    of_lower: Bound | None,
    pick: Callable[[float, float], float],
) -> Bound | None:
    if isinstance(of_upper, int | float) and isinstance(of_lower, int | float):
        return pick(of_upper, of_lower)
    # Two quantity bounds cannot be compared before they are evaluated, so the upper half's wins.
    return of_lower if of_upper is None else of_upper


def _bidirectional_range(
    graph: graphs_v1.Bidirectional | graphs_v2_unstable.Bidirectional,
    context: _ParseContext,
) -> MinimalRange | None:
    upper = _parse_range(graph.upper, context)
    lower = _parse_range(graph.lower, context)
    if upper is None:
        return lower
    if lower is None:
        return upper
    # The graph draws both halves around one axis, so its range has to span both. Each end widens on
    # its own: taking only the upper half's whenever any single bound was a quantity threw away the
    # ends that could be compared.
    return MinimalRange(
        lower=_widest_bound(upper.lower, lower.lower, min),
        upper=_widest_bound(upper.upper, lower.upper, max),
    )


def build_curve(
    quantity: QuantityProtocol,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> Curve:
    return Curve(
        quantity=quantity,
        attributes=quantity.attributes(localizer, registered_metrics) or FALLBACK_ATTRIBUTES,
    )


def _parse_lines(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    context: _ParseContext,
    *,
    inverse: bool,
) -> tuple[Sequence[Stack], Sequence[Line], Sequence[Rule]]:
    def _curve(q: _ApiQuantity) -> Curve:
        return build_curve(
            _parse_quantity(q, context), context.localizer, context.registered_metrics
        )

    stack_members = [_curve(q) for q in graph.compound_lines if not _is_scalar(q)]
    stacks = [Stack(members=stack_members, inverse=inverse)] if stack_members else []
    lines = [
        Line(curve=_curve(q), inverse=inverse) for q in graph.simple_lines if not _is_scalar(q)
    ]
    rules = [
        Rule(curve=_curve(q), inverse=inverse)
        for q in (*graph.compound_lines, *graph.simple_lines)
        if _is_scalar(q)
    ]
    return stacks, lines, rules


def parse_graph_from_api(
    graph: (
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ),
    services: Sequence[Service],
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    *,
    kind: str,
    quantity_builder: QuantityBuilderProtocol = build_single_quantity,
) -> Graph:
    context = _ParseContext(
        services=services,
        quantity_builder=quantity_builder,
        localizer=localizer,
        registered_metrics=registered_metrics,
    )
    match graph:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            stacks, lines, rules = _parse_lines(graph, context, inverse=False)
            return Graph(
                name=graph.name,
                title=graph.title.localize(localizer),
                kind=kind,
                vertical_range=_parse_range(graph, context),
                stacks=stacks,
                lines=lines,
                rules=rules,
            )
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            upper_stacks, upper_lines, upper_rules = _parse_lines(
                graph.upper, context, inverse=False
            )
            lower_stacks, lower_lines, lower_rules = _parse_lines(
                graph.lower, context, inverse=True
            )
            return Graph(
                name=graph.name,
                title=graph.title.localize(localizer),
                kind=kind,
                vertical_range=_bidirectional_range(graph, context),
                stacks=[*upper_stacks, *lower_stacks],
                lines=[*upper_lines, *lower_lines],
                rules=[*upper_rules, *lower_rules],
            )
        case _:
            assert_never(graph)
