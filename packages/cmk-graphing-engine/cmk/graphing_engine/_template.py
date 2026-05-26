#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Sequence
from dataclasses import dataclass

from ._discovery import DiscoveredGraph
from ._fetch import FetchRRD
from ._objects import Bidirectional, Graph, MetricName, StackGroup
from ._options import CommonOptions, ServiceRef


@dataclass(frozen=True, kw_only=True)
class TemplateDiscoveryOptions:
    common: CommonOptions
    service: ServiceRef
    registered_graphs: Sequence[Graph | Bidirectional]


@dataclass(frozen=True, kw_only=True)
class TemplateOptions:
    common: CommonOptions
    service: ServiceRef


def _matches(
    graph: Graph,
    names: Sequence[MetricName],
    available: Container[MetricName],
) -> bool:
    if any(name in available for name in graph.conflicting):
        return False
    optional = frozenset(graph.optional)
    return all(name in available for name in names if name not in optional)


@dataclass(frozen=True, kw_only=True)
class _GraphMatch:
    metric_names: Sequence[MetricName]
    matched: bool


def _walk(
    graph: Graph | Bidirectional,
    available: Container[MetricName],
) -> _GraphMatch:
    match graph:
        case Graph():
            names = graph.metric_names()
            return _GraphMatch(metric_names=names, matched=_matches(graph, names, available))
        case Bidirectional():
            lower_names = graph.lower.metric_names()
            upper_names = graph.upper.metric_names()
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
    for graph in options.registered_graphs:
        walk = _walk(graph, translated_metrics)
        if not walk.matched:
            continue
        claimed.update(walk.metric_names)
        discovered.append(
            DiscoveredGraph(
                graph=graph,
                options=post_options,
                scalars={
                    name: bounds
                    for name in walk.metric_names
                    if name in translated_metrics and (bounds := translated_metrics[name].bounds)
                },
            )
        )

    for name, metric in translated_metrics.items():
        if name in claimed:
            continue
        discovered.append(
            DiscoveredGraph(
                graph=Graph(
                    name=name,
                    title=name,
                    stack_groups=[StackGroup(members=[name])],
                ),
                options=post_options,
                scalars={name: metric.bounds} if metric.bounds else {},
            )
        )

    return discovered
