#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import override, Protocol

from cmk.ccc.plugin_registry import Registry
from cmk.graphing_engine import (
    ApiGraph,
    EvaluatedGraph,
    FetchDataProtocol,
    Graph,
    GraphRequest,
    MetricName,
    RequestedGraph,
    RequestedMetric,
)

from ._decoding import ensure_type
from ._evaluation_options import EvaluationOptions
from ._graph_codec import GraphCodec
from ._source import FetchDiagnostics

_METRIC_PREFIX = "METRIC_"


def legacy_graph_id(graph: Graph, registered_graphs: Sequence[ApiGraph]) -> str:
    """The graph id a built graph is addressed by in the specifications legacy stores and replays.

    A fallback single-metric graph must carry the "METRIC_" prefix legacy stores it under; without
    it the legacy recipe lookup finds neither a plug-in nor the metric.
    """
    if graph.name.startswith(_METRIC_PREFIX) or any(
        registered.name == graph.name for registered in registered_graphs
    ):
        return graph.name
    return f"{_METRIC_PREFIX}{graph.name}"


def metric_name_of(graph_id: str) -> MetricName:
    return MetricName(graph_id.removeprefix(_METRIC_PREFIX))


def graph_request_of(graph_id: str) -> GraphRequest:
    if graph_id.startswith(_METRIC_PREFIX):
        return RequestedMetric(metric_name_of(graph_id))
    return RequestedGraph(graph_id)


@dataclass(frozen=True, kw_only=True)
class EvaluatedGraphs:
    # The evaluated graphs plus the non-fatal fetch diagnostics (hit series caps, fetch errors) the
    # caller surfaces to the user - the engine evaluation itself stays diagnostics-free.
    graphs: Sequence[EvaluatedGraph]
    diagnostics: FetchDiagnostics


class FetchDataWithDiagnosticsProtocol(FetchDataProtocol, Protocol):
    # The fetch a dispatched evaluation runs on: it resolves the data and accumulates the non-fatal
    # diagnostics the evaluation reads back into its result.
    @property
    def diagnostics(self) -> FetchDiagnostics: ...


class DispatchedEvaluateProtocol(Protocol):
    # A graph type's evaluation of one graph. The request options it runs under are its own fields,
    # deserialized when it was made for those options, so it is handed nothing but the graph.
    def __call__(self, graph: Graph) -> EvaluatedGraphs: ...


@dataclass(frozen=True)
class GraphDispatcher:
    kind: str
    codec: GraphCodec
    # How to make this graph type's evaluation for the options of a request: that is where it
    # deserializes the common options and whatever else it alone needs from them.
    make_evaluate: Callable[[EvaluationOptions], DispatchedEvaluateProtocol]


class GraphDispatcherRegistry(Registry[GraphDispatcher]):
    @override
    def plugin_name(self, instance: GraphDispatcher) -> str:
        return instance.kind


graph_dispatcher_registry = GraphDispatcherRegistry()


def serialize_graphs(graphs: Sequence[Graph]) -> Mapping[str, object]:
    return {
        "graphs": [
            graph_dispatcher_registry[graph.kind].codec.serialize_graph(graph) for graph in graphs
        ]
    }


def evaluate_built_graphs(
    graphs: Sequence[Graph],
    options: EvaluationOptions,
) -> EvaluatedGraphs:
    evaluated_graphs: list[EvaluatedGraph] = []
    diagnostics = FetchDiagnostics()
    # The graphs may be of different kinds, but they share the options of one request: each graph
    # type makes its evaluation for them and evaluates the graph of its own kind.
    for graph in graphs:
        evaluated = graph_dispatcher_registry[graph.kind].make_evaluate(options)(graph)
        evaluated_graphs.extend(evaluated.graphs)
        diagnostics.limits_reached.extend(evaluated.diagnostics.limits_reached)
        diagnostics.errors.extend(evaluated.diagnostics.errors)
    return EvaluatedGraphs(graphs=evaluated_graphs, diagnostics=diagnostics)


def evaluate_graphs(
    internal: Mapping[str, object],
    options: EvaluationOptions,
) -> EvaluatedGraphs:
    graphs = []
    for serialized in ensure_type(internal["graphs"], list):
        graph = ensure_type(serialized, dict)
        dispatcher = graph_dispatcher_registry[ensure_type(graph["kind"], str)]
        graphs.append(dispatcher.codec.deserialize_graph(graph))
    return evaluate_built_graphs(graphs, options)
