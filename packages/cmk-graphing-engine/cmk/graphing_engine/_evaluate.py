#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

from ._objects import (
    Bound,
    Curve,
    CurveAttributes,
    EvaluationContext,
    FixedRange,
    Graph,
    MetricName,
    MinimalRange,
    RRDMetric,
    RRDMetricData,
    Rule,
    ServiceRef,
    TimeSeries,
    VerticalRange,
)
from ._options import TimeRange
from ._title import evaluate_title


@dataclass(frozen=True, kw_only=True)
class EvaluatedCurve:
    attributes: CurveAttributes
    value: float | None
    time_series: TimeSeries


@dataclass(frozen=True, kw_only=True)
class EvaluatedStack:
    members: Sequence[EvaluatedCurve]
    inverse: bool
    # The evaluated invisible baseline (cf. Stack.reference): the renderer uses it as the stack's
    # floor but does not draw it. None when the stack has no reference.
    reference: EvaluatedCurve | None = None


@dataclass(frozen=True, kw_only=True)
class EvaluatedLine:
    curve: EvaluatedCurve
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class EvaluatedRule:
    attributes: CurveAttributes
    value: float
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class EvaluatedMinimalRange:
    lower: float | None
    upper: float | None


@dataclass(frozen=True, kw_only=True)
class EvaluatedFixedRange:
    lower: float | None
    upper: float | None


type EvaluatedVerticalRange = EvaluatedMinimalRange | EvaluatedFixedRange


@dataclass(frozen=True, kw_only=True)
class EvaluatedGraph:
    name: str
    title: str
    vertical_range: EvaluatedVerticalRange | None
    stacks: Sequence[EvaluatedStack]
    lines: Sequence[EvaluatedLine]
    rules: Sequence[EvaluatedRule] = ()


@dataclass(frozen=True, kw_only=True)
class DiscoveredGraph:
    graph: Graph
    evaluated: EvaluatedGraph


@dataclass(frozen=True, kw_only=True)
class DiscoveredGraphs[Options]:
    options: Options
    graphs: Sequence[DiscoveredGraph]


def _evaluate_bound(bound: Bound, context: EvaluationContext) -> float | None:
    if isinstance(bound, int | float):
        return float(bound)
    return bound.evaluate_value(context)


def _evaluate_vertical_range(
    vertical_range: VerticalRange | None,
    context: EvaluationContext,
) -> EvaluatedVerticalRange | None:
    match vertical_range:
        case None:
            return None
        case MinimalRange():
            return EvaluatedMinimalRange(
                lower=_evaluate_bound(vertical_range.lower, context),
                upper=_evaluate_bound(vertical_range.upper, context),
            )
        case FixedRange():
            return EvaluatedFixedRange(
                lower=_evaluate_bound(vertical_range.lower, context),
                upper=_evaluate_bound(vertical_range.upper, context),
            )
        case _:
            assert_never(vertical_range)


def _evaluate_curve(curve: Curve, context: EvaluationContext) -> EvaluatedCurve | None:
    if not curve.quantity.is_present(context):
        return None
    return EvaluatedCurve(
        attributes=curve.attributes,
        value=curve.quantity.evaluate_value(context),
        time_series=curve.quantity.evaluate_time_series(context),
    )


def _evaluate_rule(rule: Rule, context: EvaluationContext) -> EvaluatedRule | None:
    if not rule.curve.quantity.is_present(context):
        return None
    value = rule.curve.quantity.evaluate_value(context)
    if value is None:
        return None
    return EvaluatedRule(
        attributes=rule.curve.attributes,
        value=value,
        inverse=rule.inverse,
    )


def _title_metrics(
    graph: Graph,
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> Mapping[MetricName, RRDMetricData]:
    services = {
        ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        for metric in graph.rrd_metrics()
    }
    return {
        name: data
        for service in services
        if service in translated_metrics
        for name, data in translated_metrics[service].items()
    }


def evaluate_graph(
    graph: Graph,
    metric_data: Mapping[RRDMetric, RRDMetricData],
    time_series: Mapping[RRDMetric, TimeSeries],
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
    time_range: TimeRange,
) -> EvaluatedGraph:
    context = EvaluationContext(
        metric_data=metric_data,
        time_series=time_series,
        time_range=time_range,
    )
    stacks = []
    for group in graph.stacks:
        members = [
            curve
            for member in group.members
            if (curve := _evaluate_curve(member, context)) is not None
        ]
        reference = None if group.reference is None else _evaluate_curve(group.reference, context)
        if members:
            stacks.append(
                EvaluatedStack(members=members, inverse=group.inverse, reference=reference)
            )
    lines = [
        EvaluatedLine(curve=curve, inverse=line.inverse)
        for line in graph.lines
        if (curve := _evaluate_curve(line.curve, context)) is not None
    ]
    rules = [
        evaluated
        for rule in graph.rules
        if (evaluated := _evaluate_rule(rule, context)) is not None
    ]
    return EvaluatedGraph(
        name=graph.name,
        title=evaluate_title(graph.title, _title_metrics(graph, translated_metrics)),
        vertical_range=_evaluate_vertical_range(graph.vertical_range, context),
        stacks=stacks,
        lines=lines,
        rules=rules,
    )
