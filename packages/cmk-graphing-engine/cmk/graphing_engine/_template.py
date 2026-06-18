#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable

from ._from_api import (
    metric_names_of_graph,
    metric_names_of_title,
    parse_graph_from_api,
)
from ._objects import (
    Graph,
    Line,
    MetricName,
    RRDMetric,
    RRDMetricData,
    ServiceRef,
    Stack,
)
from ._options import ConsolidationFunction, TimeRange

_PREDICT_PREFIX = "predict_"


@dataclass(frozen=True, kw_only=True)
class TemplateOptions:
    kind: ClassVar[Literal["template"]] = "template"
    time_range: TimeRange
    consolidation_function: ConsolidationFunction


def _matches(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    names: Sequence[MetricName],
    available: Container[MetricName],
) -> bool:
    if any(MetricName(name) in available for name in graph.conflicting):
        return False
    optional = frozenset(MetricName(name) for name in graph.optional)
    return all(name in available for name in names if name not in optional)


@dataclass(frozen=True, kw_only=True)
class _GraphMatch:
    metric_names: Sequence[MetricName]
    matched: bool


def _walk(
    graph: (
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ),
    available: Container[MetricName],
) -> _GraphMatch:
    match graph:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            names = metric_names_of_graph(graph)
            return _GraphMatch(metric_names=names, matched=_matches(graph, names, available))
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            title_names = metric_names_of_title(graph.title)
            lower_names = metric_names_of_graph(graph.lower)
            upper_names = metric_names_of_graph(graph.upper)
            return _GraphMatch(
                metric_names=list({*title_names, *lower_names, *upper_names}),
                matched=(
                    all(name in available for name in title_names)
                    and (
                        _matches(graph.lower, lower_names, available)
                        or _matches(graph.upper, upper_names, available)
                    )
                ),
            )


def _add_predictive_lines(
    graph: Graph,
    service: ServiceRef,
    available: Mapping[MetricName, RRDMetricData],
) -> tuple[Graph, set[MetricName]]:
    inverse_by_metric: dict[MetricName, bool] = {}
    for group in graph.stacks:
        for member in group.members:
            for metric in member.rrd_metrics():
                inverse_by_metric.setdefault(metric.metric_name, group.inverse)
    for line in graph.lines:
        for metric in line.quantity.rrd_metrics():
            inverse_by_metric.setdefault(metric.metric_name, line.inverse)

    added: list[Line] = []
    names: set[MetricName] = set()
    for base, inverse in inverse_by_metric.items():
        for predictive in (
            MetricName(f"predict_{base}"),
            MetricName(f"predict_lower_{base}"),
        ):
            if predictive in available and predictive not in names:
                added.append(
                    Line(
                        quantity=RRDMetric(
                            host_name=service.host_name,
                            service_name=service.service_name,
                            metric_name=predictive,
                        ),
                        inverse=inverse,
                    )
                )
                names.add(predictive)
    if not added:
        return graph, names
    return (
        Graph(
            name=graph.name,
            title=graph.title,
            vertical_range=graph.vertical_range,
            stacks=graph.stacks,
            lines=[*graph.lines, *added],
        ),
        names,
    )


type _GraphPlugin = (
    graphs_v1.Graph
    | graphs_v1.Bidirectional
    | graphs_v2_unstable.Graph
    | graphs_v2_unstable.Bidirectional
)


def discover_graphs(
    *,
    services: Sequence[ServiceRef],
    graph: _GraphPlugin,
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    available: Mapping[ServiceRef, Container[MetricName]],
) -> Sequence[Graph]:
    return [
        parse_graph_from_api(graph, service, metrics, localizer)
        for service in services
        if _walk(graph, available.get(service, frozenset())).matched
    ]


def build_graphs(
    *,
    service: ServiceRef,
    registered_graphs: Sequence[_GraphPlugin],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    available: Mapping[MetricName, RRDMetricData],
) -> Sequence[Graph]:
    graphs: list[Graph] = []
    claimed: set[MetricName] = set()

    def _collect(base: Graph) -> None:
        graph, predictive_names = _add_predictive_lines(base, service, available)
        claimed.update(predictive_names)
        graphs.append(graph)

    for plugin in registered_graphs:
        walk = _walk(plugin, available)
        if not walk.matched:
            continue
        claimed.update(walk.metric_names)
        _collect(parse_graph_from_api(plugin, service, metrics, localizer))

    for name in available:
        if name in claimed or name.startswith(_PREDICT_PREFIX):
            continue
        _collect(
            Graph(
                name=name,
                title=name,
                stacks=[
                    Stack(
                        members=[
                            RRDMetric(
                                host_name=service.host_name,
                                service_name=service.service_name,
                                metric_name=name,
                            )
                        ],
                        inverse=False,
                    )
                ],
            )
        )

    return graphs
