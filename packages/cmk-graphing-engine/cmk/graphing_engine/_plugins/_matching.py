#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing_engine._data._fetched import ScalarKind
from cmk.graphing_engine._data._naming import MetricName
from cmk.graphing_engine._data._units import CurveAttributes
from cmk.graphing_engine._graphs._graph import Curve, Graph, Line, Rule, Stack
from cmk.graphing_engine._quantities._quantity import fetch_leaves
from cmk.graphing_engine._rrd._fetch import FetchMetricNamesProtocol
from cmk.graphing_engine._rrd._metrics import rrd_metric_of, RRDMetric, ScalarOf
from cmk.graphing_engine._rrd._naming import PredictPrefix, Service

from ._display import metric_display_attributes, scalar_attributes
from ._graphs import build_single_quantity, parse_graph_from_api, QuantityBuilderProtocol
from ._types import ApiGraph, drawn_metric_names_of_graph


def _matches(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    names: Sequence[MetricName],
    available: Container[MetricName],
) -> bool:
    if any(MetricName(name) in available for name in graph.conflicting):
        return False
    optional = frozenset(MetricName(name) for name in graph.optional)
    required = [name for name in names if name not in optional]
    if required:
        return all(name in available for name in required)
    return any(name in available for name in names)


# A plug-in's independently matchable parts paired with the metric names they draw: one part for a
# plain graph, the lower and the upper one for a bidirectional graph. The names depend on the plug-in
# alone, so they are resolved once and then matched against each service's available names.
type _MatchableParts = Sequence[
    tuple[graphs_v1.Graph | graphs_v2_unstable.Graph, Sequence[MetricName]]
]


def _matchable_parts(graph: ApiGraph) -> _MatchableParts:
    match graph:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            return [(graph, drawn_metric_names_of_graph(graph))]
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            return [
                (graph.lower, drawn_metric_names_of_graph(graph.lower)),
                (graph.upper, drawn_metric_names_of_graph(graph.upper)),
            ]


def _add_predictive_lines(
    graph: Graph,
    service: Service,
    available: Container[MetricName],
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> tuple[Graph, set[MetricName]]:
    inverse_by_metric: dict[MetricName, bool] = {}
    for quantity, inverse in graph.drawn_quantities():
        for metric in fetch_leaves(quantity):
            if isinstance(metric, RRDMetric):
                inverse_by_metric.setdefault(metric.metric_name, inverse)

    added: list[Line] = []
    names: set[MetricName] = set()
    for base, inverse in inverse_by_metric.items():
        for predictive in (
            MetricName(f"{PredictPrefix.UPPER}{base}"),
            MetricName(f"{PredictPrefix.LOWER}{base}"),
        ):
            if predictive in available and predictive not in names:
                added.append(
                    Line(
                        curve=Curve(
                            quantity=rrd_metric_of(service, predictive),
                            attributes=metric_display_attributes(
                                predictive, localizer, registered_metrics
                            ),
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
            kind=graph.kind,
            vertical_range=graph.vertical_range,
            omit_zero_curves=graph.omit_zero_curves,
            stacks=graph.stacks,
            lines=[*graph.lines, *added],
            rules=graph.rules,
            regions=graph.regions,
        ),
        names,
    )


_THRESHOLD_KINDS = (
    ScalarKind.WARNING,
    ScalarKind.CRITICAL,
    ScalarKind.LOWER_WARNING,
    ScalarKind.LOWER_CRITICAL,
)


def threshold_rules(
    metric: RRDMetric, metric_attributes: CurveAttributes, localizer: Callable[[str], str]
) -> Sequence[Rule]:
    return [
        Rule(
            curve=Curve(
                quantity=ScalarOf(metric=metric, scalar_kind=scalar_kind),
                attributes=scalar_attributes(metric_attributes, scalar_kind, localizer),
            ),
            inverse=False,
        )
        for scalar_kind in _THRESHOLD_KINDS
    ]


@dataclass(frozen=True)
class RequestedGraph:
    name: str


@dataclass(frozen=True)
class RequestedMetric:
    metric_name: MetricName


type GraphRequest = RequestedGraph | RequestedMetric


def build_matched_graphs(
    *,
    localizer: Callable[[str], str],
    fetch_metric_names: FetchMetricNamesProtocol,
    kind: str,
    registered_graphs: Sequence[ApiGraph],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    quantity_builder: QuantityBuilderProtocol = build_single_quantity,
    request: GraphRequest | None = None,
) -> Sequence[Graph]:
    names_by_service = fetch_metric_names()
    # The metric-name fetch returns the services tagged with their resolved site; build from those so
    # the metrics carry it.
    resolved = list(names_by_service)
    available = frozenset(itertools.chain.from_iterable(names_by_service.values()))
    single_service = resolved[0] if len(resolved) == 1 else None
    matched_graphs: list[Graph] = []
    claimed: set[MetricName] = set()

    def _collect(base: Graph) -> None:
        # Discard non-requested graphs the moment their name is known, before the predictive-line
        # work, rather than building every graph and filtering afterwards.
        if isinstance(request, RequestedGraph) and base.name != request.name:
            return
        # A predictive line is a single-service concept; a graph over multiple services has none (nor
        # rules or a quantity range bound, which the parse already left out).
        if single_service is None:
            matched_graphs.append(base)
            return
        graph, predictive_names = _add_predictive_lines(
            base, single_service, available, localizer, registered_metrics
        )
        claimed.update(predictive_names)
        matched_graphs.append(graph)

    def _fallback_rules(name: MetricName) -> Sequence[Rule]:
        if single_service is None:
            return ()
        return threshold_rules(
            rrd_metric_of(single_service, name),
            metric_display_attributes(name, localizer, registered_metrics),
            localizer,
        )

    def _single_metric_graph(name: MetricName) -> Graph:
        return Graph(
            name=name,
            title=metric_display_attributes(name, localizer, registered_metrics).title,
            kind=kind,
            stacks=[
                Stack(
                    members=[
                        Curve(
                            quantity=quantity_builder(
                                [rrd_metric_of(service, name) for service in resolved]
                            ),
                            attributes=metric_display_attributes(
                                name, localizer, registered_metrics
                            ),
                        )
                    ],
                    inverse=False,
                )
            ],
            rules=_fallback_rules(name),
        )

    # A single-metric request names no plug-in, and a plug-in graph drawing that metric claims it,
    # which keeps the loop below from reaching it. Answer such a request on its own.
    if isinstance(request, RequestedMetric):
        if request.metric_name in available:
            _collect(_single_metric_graph(request.metric_name))
        return matched_graphs

    for plugin in registered_graphs:
        parts = _matchable_parts(plugin)
        if not any(
            _matches(part, names, service_names)
            for service_names in names_by_service.values()
            for part, names in parts
        ):
            continue
        claimed.update(name for _part, names in parts for name in names)
        _collect(
            parse_graph_from_api(
                plugin,
                resolved,
                localizer,
                registered_metrics,
                kind=kind,
                quantity_builder=quantity_builder,
            )
        )

    for name in sorted(available):
        if name in claimed or name.startswith(PredictPrefix.UPPER):
            continue
        _collect(_single_metric_graph(name))

    return matched_graphs
