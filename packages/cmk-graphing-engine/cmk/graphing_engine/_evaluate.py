#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

from ._objects import (
    Bound,
    EvaluationContext,
    FixedRange,
    Graph,
    MetricName,
    MinimalRange,
    Quantity,
    RRDMetricData,
    RRDMetricRef,
    ServiceRef,
    TimeSeries,
    Unit,
    VerticalRange,
)
from ._options import TimeRange
from ._title import evaluate_title


@dataclass(frozen=True, kw_only=True)
class EvaluatedCurve:
    title: str
    unit: Unit
    color: str
    value: float | None
    time_series: TimeSeries


@dataclass(frozen=True, kw_only=True)
class EvaluatedStack:
    members: Sequence[EvaluatedCurve]
    inverse: bool


@dataclass(frozen=True, kw_only=True)
class EvaluatedLine:
    curve: EvaluatedCurve
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


@dataclass(frozen=True, kw_only=True)
class DiscoveredGraph[Options]:
    graph: Graph
    options: Options
    title: str
    vertical_range: EvaluatedVerticalRange | None
    stacks: Sequence[EvaluatedStack]
    lines: Sequence[EvaluatedLine]


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


def _evaluate_curve(quantity: Quantity, context: EvaluationContext) -> EvaluatedCurve | None:
    if (attributes := quantity.evaluate_attributes(context)) is None:
        return None
    return EvaluatedCurve(
        title=attributes.title,
        unit=attributes.unit,
        color=attributes.color,
        value=quantity.evaluate_value(context),
        time_series=quantity.evaluate_time_series(context),
    )


def _title_metrics(
    graph: Graph,
    translated_metrics: Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]],
) -> Mapping[ServiceRef, Mapping[MetricName, RRDMetricData]]:
    services = {
        ServiceRef(host_name=metric.host_name, service_name=metric.service_name)
        for metric in graph.rrd_metrics()
    }
    return {
        service: translated_metrics[service]
        for service in services
        if service in translated_metrics
    }


def evaluate_graph(
    graph: Graph,
    metric_data: Mapping[RRDMetricRef, RRDMetricData],
    time_series: Mapping[RRDMetricRef, TimeSeries],
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
        if members:
            stacks.append(EvaluatedStack(members=members, inverse=group.inverse))
    lines = [
        EvaluatedLine(curve=curve, inverse=line.inverse)
        for line in graph.lines
        if (curve := _evaluate_curve(line.quantity, context)) is not None
    ]
    return EvaluatedGraph(
        name=graph.name,
        title=evaluate_title(graph.title, _title_metrics(graph, translated_metrics)),
        vertical_range=_evaluate_vertical_range(graph.vertical_range, context),
        stacks=stacks,
        lines=lines,
    )
