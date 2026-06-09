#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container, Sequence
from dataclasses import dataclass

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable

from ._discovery import DiscoveredGraph
from ._fetch import FetchRRD
from ._from_api import metric_names_of_graph, parse_graph_from_api
from ._objects import Graph, MetricName, RRDMetric, StackGroup
from ._options import CommonOptions, ConsolidationFunction, ServiceRef


@dataclass(frozen=True, kw_only=True)
class TemplateDiscoveryOptions:
    common: CommonOptions
    service: ServiceRef
    consolidation_function: ConsolidationFunction
    localizer: Callable[[str], str]
    registered_graphs: Sequence[
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ]


@dataclass(frozen=True, kw_only=True)
class TemplateOptions:
    common: CommonOptions
    service: ServiceRef


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
            lower_names = metric_names_of_graph(graph.lower)
            upper_names = metric_names_of_graph(graph.upper)
            return _GraphMatch(
                metric_names=list(set((*lower_names, *upper_names))),
                matched=(
                    _matches(graph.lower, lower_names, available)
                    or _matches(graph.upper, upper_names, available)
                ),
            )


def discover_template_graphs(
    options: TemplateDiscoveryOptions,
    *,
    rrd: FetchRRD,
) -> Sequence[DiscoveredGraph[TemplateOptions]]:
    translated_metrics = rrd.translated_metrics([options.service]).get(options.service, {})
    post_options = TemplateOptions(common=options.common, service=options.service)

    discovered: list[DiscoveredGraph[TemplateOptions]] = []
    claimed: set[MetricName] = set()
    for plugin in options.registered_graphs:
        walk = _walk(plugin, translated_metrics)
        if not walk.matched:
            continue
        claimed.update(walk.metric_names)
        graph = parse_graph_from_api(
            plugin,
            options.localizer,
            options.service,
            options.consolidation_function,
        )
        discovered.append(
            DiscoveredGraph(
                graph=graph,
                options=post_options,
                scalars=graph.scalars(translated_metrics),
            )
        )

    for name in translated_metrics:
        if name in claimed:
            continue
        graph = Graph(
            name=name,
            title=name,
            stack_groups=[
                StackGroup(
                    members=[
                        RRDMetric(
                            host_name=options.service.host_name,
                            service_name=options.service.service_name,
                            metric_name=name,
                            consolidation_function=options.consolidation_function,
                        )
                    ]
                )
            ],
        )
        discovered.append(
            DiscoveredGraph(
                graph=graph,
                options=post_options,
                scalars=graph.scalars(translated_metrics),
            )
        )

    return discovered
