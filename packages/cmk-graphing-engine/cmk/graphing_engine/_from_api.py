#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, Protocol

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable

from ._api_plugins import (
    ApiQuantity,
    ApiScalar,
    is_scalar,
    metric_names_in_quantity,
    operands_of,
)
from ._display import (
    FALLBACK_ATTRIBUTES,
    metric_display_attributes,
    parse_color,
    parse_unit,
)
from ._graph import Bound, Curve, Graph, Line, MinimalRange, Rule, Stack
from ._naming import Service
from ._quantities import (
    Constant,
    Difference,
    Fraction,
    Product,
    rrd_metric_of,
    RRDMetric,
    ScalarKind,
    ScalarOf,
    Sum,
)
from ._quantity import QuantityProtocol
from ._units import CurveAttributes


def scalar_kind_of(scalar: ApiScalar) -> ScalarKind:
    match scalar:
        case metrics_v1.WarningOf():
            return ScalarKind.WARNING
        case metrics_v1.CriticalOf():
            return ScalarKind.CRITICAL
        case metrics_v2_unstable.LowerWarningOf():
            return ScalarKind.LOWER_WARNING
        case metrics_v2_unstable.LowerCriticalOf():
            return ScalarKind.LOWER_CRITICAL
        case metrics_v1.MinimumOf():
            return ScalarKind.MINIMUM
        case metrics_v1.MaximumOf():
            return ScalarKind.MAXIMUM
        case _:
            assert_never(scalar)


class QuantityBuilderProtocol(Protocol):
    """Combines what a graph draws for each matched object into the one quantity drawing them."""

    def __call__(self, per_object: Sequence[QuantityProtocol]) -> QuantityProtocol: ...


def build_single_quantity(per_object: Sequence[QuantityProtocol]) -> QuantityProtocol:
    (quantity,) = per_object
    return quantity


def drawn_quantity(
    metric_name: str,
    services: Sequence[Service],
    quantity_builder: QuantityBuilderProtocol,
) -> QuantityProtocol:
    return quantity_builder([rrd_metric_of(service, metric_name) for service in services])


@dataclass(frozen=True)
class _ObjectContext:
    """One of the objects a graph was matched on, to build what it draws for that object."""

    service: Service
    localizer: Callable[[str], str]
    registered_metrics: Mapping[str, metrics_v1.Metric]

    def metric(self, metric_name: str) -> RRDMetric:
        return rrd_metric_of(self.service, metric_name)


@dataclass(frozen=True)
class _ParseContext:
    services: Sequence[Service]
    quantity_builder: QuantityBuilderProtocol
    localizer: Callable[[str], str]
    registered_metrics: Mapping[str, metrics_v1.Metric]

    def _of(self, service: Service) -> _ObjectContext:
        return _ObjectContext(service, self.localizer, self.registered_metrics)

    def single_object(self) -> _ObjectContext | None:
        # A rule names one object's thresholds; over several matched ones there is none to name them
        # against, so no rule is built.
        return self._of(self.services[0]) if len(self.services) == 1 else None

    def object_for(self, bound: ApiQuantity) -> _ObjectContext | None:
        # A bound naming a metric is read from one object; over several matched ones there is none, so
        # that end is left to auto-scale. A bound of constants alone is read without one.
        if any(metric_names_in_quantity(bound)):
            return self.single_object()
        return self._of(self.services[0])

    def drawn(self, quantity: ApiQuantity) -> QuantityProtocol:
        # Built once per matched object and combined, so an operation only ever takes that object's
        # operands - never a quantity spanning the objects, which cannot be an operand.
        return self.quantity_builder(
            [_parse_quantity(quantity, self._of(service)) for service in self.services]
        )


def _curve_display(quantity: ApiQuantity, context: _ObjectContext) -> CurveAttributes:
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
                unit=_curve_display(operands_of(quantity)[0], context).unit,
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


def _parse_quantity(quantity: ApiQuantity, context: _ObjectContext) -> QuantityProtocol:
    match quantity:
        case str():
            return context.metric(quantity)
        case metrics_v1.Constant():
            return Constant(quantity.value, display=_curve_display(quantity, context))
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
        ):
            return ScalarOf(
                metric=context.metric(quantity.metric_name),
                scalar_kind=scalar_kind_of(quantity),
            )
        case metrics_v1.MinimumOf() | metrics_v1.MaximumOf():
            return ScalarOf(
                metric=context.metric(quantity.metric_name),
                scalar_kind=scalar_kind_of(quantity),
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


def _parse_bound(bound: int | float | ApiQuantity, context: _ParseContext) -> Bound | None:
    if isinstance(bound, int | float):
        return bound
    object_context = context.object_for(bound)
    return None if object_context is None else _parse_quantity(bound, object_context)


def _parse_range(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    context: _ParseContext,
) -> MinimalRange | None:
    if graph.minimal_range is None:
        return None
    lower = _parse_bound(graph.minimal_range.lower, context)
    upper = _parse_bound(graph.minimal_range.upper, context)
    if lower is None and upper is None:
        return None
    return MinimalRange(lower=lower, upper=upper)


def _widest_bound(
    of_upper: Bound | None,
    of_lower: Bound | None,
    pick: Callable[[float, float], float],
) -> Bound | None:
    if isinstance(of_upper, int | float) and isinstance(of_lower, int | float):
        return pick(of_upper, of_lower)
    # Two quantity bounds cannot be compared before they are evaluated, so the upper half's wins; a
    # half whose end was dropped has none, and then the other half's end is the range.
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
    def _curve(quantity: QuantityProtocol) -> Curve:
        return build_curve(quantity, context.localizer, context.registered_metrics)

    stack_members = [_curve(context.drawn(q)) for q in graph.compound_lines if not is_scalar(q)]
    stacks = [Stack(members=stack_members, inverse=inverse)] if stack_members else []
    lines = [
        Line(curve=_curve(context.drawn(q)), inverse=inverse)
        for q in graph.simple_lines
        if not is_scalar(q)
    ]
    single_object = context.single_object()
    rules: Sequence[Rule] = (
        ()
        if single_object is None
        else [
            Rule(curve=_curve(_parse_quantity(q, single_object)), inverse=inverse)
            for q in (*graph.compound_lines, *graph.simple_lines)
            if is_scalar(q)
        ]
    )
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
