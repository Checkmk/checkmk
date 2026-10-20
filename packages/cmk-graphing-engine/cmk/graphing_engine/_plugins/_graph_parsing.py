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
from cmk.graphing_engine._data._units import CurveAttributes
from cmk.graphing_engine._graphs._graph import Bound, Curve, Graph, Line, MinimalRange, Rule, Stack
from cmk.graphing_engine._quantities._quantity import QuantityProtocol
from cmk.graphing_engine._rrd._naming import Service

from ._quantity_parsing import attributes_of_quantity, parse_quantity
from ._types import ApiGraph, ApiQuantity, is_scalar, metric_names_in_quantity


class QuantityBuilderProtocol(Protocol):
    def __call__(self, per_object: Sequence[QuantityProtocol]) -> QuantityProtocol: ...


def build_single_quantity(per_object: Sequence[QuantityProtocol]) -> QuantityProtocol:
    (quantity,) = per_object
    return quantity


@dataclass(frozen=True)
class _ParseContext:
    services: Sequence[Service]
    quantity_builder: QuantityBuilderProtocol
    localizer: Callable[[str], str]
    registered_metrics: Mapping[str, metrics_v1.Metric]

    def single_object(self) -> Service | None:
        return self.services[0] if len(self.services) == 1 else None

    def object_for(self, bound: ApiQuantity) -> Service | None:
        if any(metric_names_in_quantity(bound)):
            return self.single_object()
        return self.services[0]

    def attributes(self, quantity: ApiQuantity) -> CurveAttributes:
        return attributes_of_quantity(quantity, self.localizer, self.registered_metrics)

    def drawn(self, quantity: ApiQuantity) -> QuantityProtocol:
        return self.quantity_builder(
            [parse_quantity(quantity, service) for service in self.services]
        )


def _parse_bound(bound: int | float | ApiQuantity, context: _ParseContext) -> Bound | None:
    if isinstance(bound, int | float):
        return bound
    service = context.object_for(bound)
    return None if service is None else parse_quantity(bound, service)


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
    return MinimalRange(
        lower=_widest_bound(upper.lower, lower.lower, min),
        upper=_widest_bound(upper.upper, lower.upper, max),
    )


def _parse_lines(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    context: _ParseContext,
    *,
    inverse: bool,
) -> tuple[Sequence[Stack], Sequence[Line], Sequence[Rule]]:
    def _curve(api_quantity: ApiQuantity, quantity: QuantityProtocol) -> Curve:
        return Curve(quantity=quantity, attributes=context.attributes(api_quantity))

    stack_members = [_curve(q, context.drawn(q)) for q in graph.compound_lines if not is_scalar(q)]
    stacks = [Stack(members=stack_members, inverse=inverse)] if stack_members else []
    lines = [
        Line(curve=_curve(q, context.drawn(q)), inverse=inverse)
        for q in graph.simple_lines
        if not is_scalar(q)
    ]
    single_object = context.single_object()
    rules: Sequence[Rule] = (
        ()
        if single_object is None
        else [
            Rule(curve=_curve(q, parse_quantity(q, single_object)), inverse=inverse)
            for q in (*graph.compound_lines, *graph.simple_lines)
            if is_scalar(q)
        ]
    )
    return stacks, lines, rules


def parse_graph_from_api(
    graph: ApiGraph,
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
