#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable

from ._from_api import (
    drawn_metric_names_of_graph,
    parse_graph_from_api,
    resolve_curve,
)
from ._objects import (
    Line,
    MetricName,
    ResolvedGraph,
    RRDMetric,
    RRDMetricData,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceRef,
    Stack,
)

_PREDICT_PREFIX = "predict_"


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
            names = drawn_metric_names_of_graph(graph)
            return _GraphMatch(metric_names=names, matched=_matches(graph, names, available))
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            # Matching is per drawn metric only; the title is not consulted (legacy parity), and a
            # bidirectional matches when either half matches.
            lower_names = drawn_metric_names_of_graph(graph.lower)
            upper_names = drawn_metric_names_of_graph(graph.upper)
            return _GraphMatch(
                metric_names=list({*lower_names, *upper_names}),
                matched=(
                    _matches(graph.lower, lower_names, available)
                    or _matches(graph.upper, upper_names, available)
                ),
            )


def _add_predictive_lines(
    graph: ResolvedGraph,
    service: ServiceRef,
    available: Container[MetricName],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
) -> tuple[ResolvedGraph, set[MetricName]]:
    inverse_by_metric: dict[MetricName, bool] = {}
    for group in graph.stacks:
        for member in group.members:
            for metric in member.quantity.rrd_metrics():
                inverse_by_metric.setdefault(metric.metric_name, group.inverse)
    for line in graph.lines:
        for metric in line.curve.quantity.rrd_metrics():
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
                        curve=resolve_curve(
                            RRDMetric(
                                host_name=service.host_name,
                                service_name=service.service_name,
                                metric_name=predictive,
                            ),
                            metrics,
                            localizer,
                        ),
                        inverse=inverse,
                    )
                )
                names.add(predictive)
    if not added:
        return graph, names
    return (
        ResolvedGraph(
            name=graph.name,
            title=graph.title,
            kind=graph.kind,
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


def match_graph_for_services(
    *,
    services: Sequence[ServiceRef],
    graph: _GraphPlugin,
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    available: Mapping[ServiceRef, Container[MetricName]],
    kind: str,
) -> Sequence[ResolvedGraph]:
    discovered: list[ResolvedGraph] = []
    for service in services:
        service_available = available.get(service, frozenset())
        if not _walk(graph, service_available).matched:
            continue
        # Add the predictive lines per service exactly as build_service_graphs does for template
        # graphs, so a combined graph includes them wherever predict_* exists (legacy combined
        # parity).
        with_predictive, _names = _add_predictive_lines(
            parse_graph_from_api(graph, service, metrics, localizer, kind=kind),
            service,
            service_available,
            metrics,
            localizer,
        )
        discovered.append(with_predictive)
    return discovered


def build_service_graphs(
    *,
    service: ServiceRef,
    registered_graphs: Sequence[_GraphPlugin],
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    available: Mapping[MetricName, RRDMetricData],
    kind: str,
) -> Sequence[ResolvedGraph]:
    """Build a service's matching template graphs plus a fallback single-metric graph per unclaimed
    metric, with each curve's display resolved inline. The fallback metric gets the four warn / crit
    (and lower) threshold rules as ScalarOf quantities (their labels / colours resolved from the kind);
    evaluation drops a rule whose level is unset. Matched plugin graphs already carry their own scalar
    rules."""
    graphs: list[ResolvedGraph] = []
    claimed: set[MetricName] = set()

    def _collect(base: ResolvedGraph) -> None:
        graph, predictive_names = _add_predictive_lines(
            base, service, available, metrics, localizer
        )
        claimed.update(predictive_names)
        graphs.append(graph)

    for plugin in registered_graphs:
        walk = _walk(plugin, available)
        if not walk.matched:
            continue
        claimed.update(walk.metric_names)
        _collect(parse_graph_from_api(plugin, service, metrics, localizer, kind=kind))

    for name in available:
        if name in claimed or name.startswith(_PREDICT_PREFIX):
            continue
        rrd_metric = RRDMetric(
            host_name=service.host_name,
            service_name=service.service_name,
            metric_name=name,
        )
        _collect(
            ResolvedGraph(
                name=name,
                title=name,
                kind=kind,
                stacks=[
                    Stack(members=[resolve_curve(rrd_metric, metrics, localizer)], inverse=False)
                ],
                rules=[
                    Rule(
                        curve=resolve_curve(
                            ScalarOf(metric=rrd_metric, kind=scalar_kind), metrics, localizer
                        ),
                        inverse=False,
                    )
                    for scalar_kind in (
                        ScalarKind.WARNING,
                        ScalarKind.CRITICAL,
                        ScalarKind.LOWER_WARNING,
                        ScalarKind.LOWER_CRITICAL,
                    )
                ],
            )
        )

    return graphs
