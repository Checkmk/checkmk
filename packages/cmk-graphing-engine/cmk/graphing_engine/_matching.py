#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Callable, Container, Iterator, Mapping, Sequence

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable

from ._api_plugins import drawn_metric_names_of_graph
from ._display import metric_display_attributes
from ._fetch import FetchMetricNamesProtocol
from ._from_api import (
    build_curve,
    build_single_quantity,
    drawn_quantity,
    parse_graph_from_api,
    QuantityBuilderProtocol,
)
from ._graph import Graph, Line, Rule, Stack
from ._naming import MetricName, Service
from ._quantities import rrd_metric_of, RRDMetric, ScalarKind, ScalarOf
from ._quantity import QuantityProtocol

_PREDICT_PREFIX = "predict_"
_METRIC_PREFIX = "METRIC_"


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


type _GraphPlugin = (
    graphs_v1.Graph
    | graphs_v1.Bidirectional
    | graphs_v2_unstable.Graph
    | graphs_v2_unstable.Bidirectional
)

# A plug-in's independently matchable parts paired with the metric names they draw: one part for a
# plain graph, the lower and the upper one for a bidirectional graph. The names depend on the plug-in
# alone, so they are resolved once and then matched against each service's available names.
type _MatchableParts = Sequence[
    tuple[graphs_v1.Graph | graphs_v2_unstable.Graph, Sequence[MetricName]]
]


def _matchable_parts(graph: _GraphPlugin) -> _MatchableParts:
    match graph:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            return [(graph, drawn_metric_names_of_graph(graph))]
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            return [
                (graph.lower, drawn_metric_names_of_graph(graph.lower)),
                (graph.upper, drawn_metric_names_of_graph(graph.upper)),
            ]


def _drawn_quantities(graph: Graph) -> Iterator[tuple[QuantityProtocol, bool]]:
    for group in graph.stacks:
        for member in group.members:
            yield member.quantity, group.inverse
    for line in graph.lines:
        yield line.curve.quantity, line.inverse


def _add_predictive_lines(
    graph: Graph,
    service: Service,
    available: Container[MetricName],
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> tuple[Graph, set[MetricName]]:
    inverse_by_metric: dict[MetricName, bool] = {}
    for quantity, inverse in _drawn_quantities(graph):
        for metric in quantity.metrics():
            if isinstance(metric, RRDMetric):
                inverse_by_metric.setdefault(metric.metric_name, inverse)

    added: list[Line] = []
    names: set[MetricName] = set()
    for base, inverse in inverse_by_metric.items():
        for predictive in (
            MetricName(f"{_PREDICT_PREFIX}{base}"),
            MetricName(f"{_PREDICT_PREFIX}lower_{base}"),
        ):
            if predictive in available and predictive not in names:
                added.append(
                    Line(
                        curve=build_curve(
                            rrd_metric_of(service, predictive), localizer, registered_metrics
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
            stacks=graph.stacks,
            lines=[*graph.lines, *added],
            rules=graph.rules,
        ),
        names,
    )


_FALLBACK_SCALAR_KINDS = (
    ScalarKind.WARNING,
    ScalarKind.CRITICAL,
    ScalarKind.LOWER_WARNING,
    ScalarKind.LOWER_CRITICAL,
)


def _matches_graph_name(graph: Graph, graph_name: str) -> bool:
    # Legacy configs and autocompleters identify single-metric graphs as "METRIC_<name>", while the
    # engine names the corresponding fallback graphs after the bare metric name.
    return graph.name == graph_name or graph.name == graph_name.removeprefix(_METRIC_PREFIX)


def _requested_single_metric(graph_name: str | None) -> MetricName | None:
    if graph_name is None or not graph_name.startswith(_METRIC_PREFIX):
        return None
    return MetricName(graph_name.removeprefix(_METRIC_PREFIX))


def build_matched_graphs(
    *,
    localizer: Callable[[str], str],
    fetch_metric_names: FetchMetricNamesProtocol,
    kind: str,
    registered_graphs: Sequence[_GraphPlugin],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    quantity_builder: QuantityBuilderProtocol = build_single_quantity,
    graph_name: str | None = None,
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
        if graph_name is not None and not _matches_graph_name(base, graph_name):
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
        metric = rrd_metric_of(single_service, name)
        return [
            Rule(
                curve=build_curve(
                    ScalarOf(metric=metric, scalar_kind=scalar_kind), localizer, registered_metrics
                ),
                inverse=False,
            )
            for scalar_kind in _FALLBACK_SCALAR_KINDS
        ]

    def _single_metric_graph(name: MetricName) -> Graph:
        return Graph(
            name=name,
            title=metric_display_attributes(name, localizer, registered_metrics).title,
            kind=kind,
            stacks=[
                Stack(
                    members=[
                        build_curve(
                            drawn_quantity(name, resolved, quantity_builder),
                            localizer,
                            registered_metrics,
                        )
                    ],
                    inverse=False,
                )
            ],
            rules=_fallback_rules(name),
        )

    # A single-metric request names no plug-in, and a plug-in graph drawing that metric claims it,
    # which keeps the loop below from reaching it. Answer such a request on its own.
    if (single_metric := _requested_single_metric(graph_name)) is not None:
        if single_metric in available:
            _collect(_single_metric_graph(single_metric))
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

    for name in available:
        if name in claimed or name.startswith(_PREDICT_PREFIX):
            continue
        _collect(_single_metric_graph(name))

    return matched_graphs
