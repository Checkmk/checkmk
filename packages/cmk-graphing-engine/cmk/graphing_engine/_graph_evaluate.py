#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import colorsys
import enum
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import assert_never

from ._fetch import fetch_evaluation_context, FetchDataProtocol
from ._fetched import MACRO_SERIES_ID, SeriesAttributes
from ._graph import FixedRange, Graph, MinimalRange, Rule, VerticalRange
from ._quantity import Bound, Curve, EvaluationContext, first_value, QuantityProtocol
from ._timeseries import ConsolidationFunction, TimeRange, TimeSeries
from ._title import evaluate_title
from ._units import CurveAttributes


@dataclass(frozen=True, kw_only=True)
class EvaluatedCurve:
    id: str
    attributes: CurveAttributes
    value: float | None
    time_series: TimeSeries
    source_id: str | None = None
    # The attributes of the series the curve was evaluated from, e.g. a metric backend's resource,
    # scope and data point attributes. Empty for a curve fetched from RRDs.
    series_attributes: SeriesAttributes = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class EvaluatedStack:
    members: Sequence[EvaluatedCurve]
    inverse: bool
    reference: EvaluatedCurve | None = None


@dataclass(frozen=True, kw_only=True)
class EvaluatedLine:
    curve: EvaluatedCurve
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class EvaluatedRule:
    id: str
    attributes: CurveAttributes
    value: float
    inverse: bool


class VerticalRangeKind(enum.StrEnum):
    MINIMAL = "minimal"
    FIXED = "fixed"


@dataclass(frozen=True, kw_only=True)
class EvaluatedVerticalRange:
    range_kind: VerticalRangeKind
    lower: float | None
    upper: float | None


@dataclass(frozen=True, kw_only=True)
class EvaluatedGraph:
    name: str
    title: str
    vertical_range: EvaluatedVerticalRange | None
    stacks: Sequence[EvaluatedStack]
    lines: Sequence[EvaluatedLine]
    rules: Sequence[EvaluatedRule] = ()


def _evaluate_bound(bound: Bound | None, context: EvaluationContext) -> float | None:
    if bound is None:
        return None
    if isinstance(bound, int | float):
        return float(bound)
    return first_value(bound.evaluate(context))


def _evaluate_vertical_range(
    vertical_range: VerticalRange | None,
    context: EvaluationContext,
) -> EvaluatedVerticalRange | None:
    match vertical_range:
        case None:
            return None
        case MinimalRange():
            range_kind = VerticalRangeKind.MINIMAL
        case FixedRange():
            range_kind = VerticalRangeKind.FIXED
        case _:
            assert_never(vertical_range)
    return EvaluatedVerticalRange(
        range_kind=range_kind,
        lower=_evaluate_bound(vertical_range.lower, context),
        upper=_evaluate_bound(vertical_range.upper, context),
    )


def _create_id(quantity: QuantityProtocol, *, inverse: bool, seen: Counter[str]) -> str:
    base = ("-" if inverse else "") + quantity.ident()
    seen[base] += 1
    return base if seen[base] == 1 else f"{base}#{seen[base]}"


def _distinct_color(index: int) -> str:
    # Golden-ratio hue stepping gives each fanned-out curve a visually distinct colour.
    hue = (index * 0.618033988749895) % 1.0
    red, green, blue = colorsys.hls_to_rgb(hue, 0.5, 0.6)
    return f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"


def _resolve_series_title(title: str, label_macros: Mapping[str, str], *, fanned: bool) -> str:
    resolved = title
    for macro, value in label_macros.items():
        resolved = resolved.replace(macro, value)
    if resolved != title:
        # The title carried macros (e.g. a query line) - resolve them per series, at any count.
        return resolved
    if fanned and (series_id := label_macros.get(MACRO_SERIES_ID, "")):
        # A macro-less title fanned into several series (e.g. a combined graph) - fall back to
        # appending the series id so the curves stay distinguishable.
        return f"{title} - {series_id}" if title else series_id
    return title


def _series_curve_attributes(
    attributes: CurveAttributes, *, index: int, fanned: bool, label_macros: Mapping[str, str]
) -> CurveAttributes:
    return CurveAttributes(
        title=_resolve_series_title(attributes.title, label_macros, fanned=fanned),
        unit=attributes.unit,
        color=_distinct_color(index) if fanned else attributes.color,
    )


def _evaluate_curve(
    curve: Curve, *, inverse: bool, seen: Counter[str], context: EvaluationContext
) -> Sequence[EvaluatedCurve]:
    results = curve.quantity.evaluate(context)
    fanned = len(results) > 1
    return [
        EvaluatedCurve(
            id=_create_id(curve.quantity, inverse=inverse, seen=seen),
            attributes=_series_curve_attributes(
                curve.attributes, index=index, fanned=fanned, label_macros=evaluated.label_macros
            ),
            value=evaluated.value,
            time_series=evaluated.time_series,
            source_id=curve.source_id,
            series_attributes=evaluated.series_attributes,
        )
        for index, evaluated in enumerate(results)
    ]


def _evaluate_rule(rule: Rule, rule_id: str, context: EvaluationContext) -> EvaluatedRule | None:
    value = first_value(rule.curve.quantity.evaluate(context))
    if value is None:
        return None
    return EvaluatedRule(
        id=rule_id,
        attributes=rule.curve.attributes,
        value=value,
        inverse=rule.inverse,
    )


def _evaluate_graph(graph: Graph, context: EvaluationContext) -> EvaluatedGraph:
    seen: Counter[str] = Counter()
    stacks = []
    for group in graph.stacks:
        members = [
            member_curve
            for member in group.members
            for member_curve in _evaluate_curve(
                member, inverse=group.inverse, seen=seen, context=context
            )
        ]
        reference = None
        if group.reference is not None:
            references = _evaluate_curve(
                group.reference, inverse=group.inverse, seen=seen, context=context
            )
            reference = references[0] if references else None
        if members:
            stacks.append(
                EvaluatedStack(members=members, inverse=group.inverse, reference=reference)
            )
    lines = [
        EvaluatedLine(curve=line_curve, inverse=line.inverse)
        for line in graph.lines
        for line_curve in _evaluate_curve(
            line.curve, inverse=line.inverse, seen=seen, context=context
        )
    ]
    rules = []
    for rule in graph.rules:
        # The id has to be minted before the rule is known to be present: it counts the quantity
        # towards the graph's seen ones either way.
        rule_id = _create_id(rule.curve.quantity, inverse=rule.inverse, seen=seen)
        if (evaluated := _evaluate_rule(rule, rule_id, context)) is not None:
            rules.append(evaluated)
    return EvaluatedGraph(
        name=graph.name,
        title=evaluate_title(graph.title, graph.metrics(), context),
        vertical_range=_evaluate_vertical_range(graph.vertical_range, context),
        stacks=stacks,
        lines=lines,
        rules=rules,
    )


def evaluate_graphs(
    *,
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    graphs: Sequence[Graph],
    fetch_data: FetchDataProtocol,
) -> Sequence[EvaluatedGraph]:
    context = fetch_evaluation_context(
        consolidation_function=consolidation_function,
        time_range=time_range,
        graphs=graphs,
        fetch_data=fetch_data,
    )
    return [_evaluate_graph(graph, context) for graph in graphs]
