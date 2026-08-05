#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import override, Protocol

from cmk.ccc.plugin_registry import Registry
from cmk.graphing_engine import (
    ConsolidationFunction,
    EvaluatedGraph,
    FetchDataProtocol,
    Graph,
    TimeRange,
)

from ._engine_codec import (
    consolidation_function_of,
    ensure_type,
    GraphCodec,
    time_range_of,
)
from ._engine_source import FetchDiagnostics
from ._from_api import GraphFromAPI


def legacy_graph_id(graph: Graph, registered_graphs: Sequence[GraphFromAPI]) -> str:
    """The graph id a built graph is addressed by in the specifications legacy stores and replays.

    A fallback single-metric graph must carry the "METRIC_" prefix legacy stores it under; without
    it the legacy recipe lookup finds neither a plug-in nor the metric.
    """
    if graph.name.startswith("METRIC_") or any(
        registered.name == graph.name for registered in registered_graphs
    ):
        return graph.name
    return f"METRIC_{graph.name}"


@dataclass(frozen=True, kw_only=True)
class CommonGraphOptions:
    consolidation_function: ConsolidationFunction
    time_range: TimeRange

    @classmethod
    def from_request_options(cls, options: Mapping[str, object]) -> CommonGraphOptions:
        return cls(
            consolidation_function=consolidation_function_of(options),
            time_range=time_range_of(options),
        )


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
class EngineGraphDispatcher:
    kind: str
    codec: GraphCodec
    # How to make this graph type's evaluation for the options of a request: that is where it
    # deserializes the common options and whatever else it alone needs from them.
    make_evaluate: Callable[[Mapping[str, object]], DispatchedEvaluateProtocol]

    def serialize(self, graph: Graph) -> Mapping[str, object]:
        return self.codec.serialize_graph(graph)

    def deserialize(self, graph: Mapping[str, object]) -> Graph:
        return self.codec.deserialize_graph(graph)


class EngineGraphDispatcherRegistry(Registry[EngineGraphDispatcher]):
    @override
    def plugin_name(self, instance: EngineGraphDispatcher) -> str:
        return instance.kind


engine_graph_dispatcher_registry = EngineGraphDispatcherRegistry()


def serialize_graphs(graphs: Sequence[Graph]) -> Mapping[str, object]:
    return {
        "graphs": [
            engine_graph_dispatcher_registry[graph.kind].serialize(graph) for graph in graphs
        ]
    }


def evaluate_graphs(
    internal: Mapping[str, object],
    options: Mapping[str, object],
) -> EvaluatedGraphs:
    evaluated_graphs: list[EvaluatedGraph] = []
    diagnostics = FetchDiagnostics()
    # The definition may hold graphs of different kinds, but they share the options of one request:
    # each graph type makes its evaluation for them, then reads its graph back and evaluates it.
    for serialized in ensure_type(internal["graphs"], list):
        graph = ensure_type(serialized, dict)
        dispatcher = engine_graph_dispatcher_registry[ensure_type(graph["kind"], str)]
        evaluated = dispatcher.make_evaluate(options)(dispatcher.deserialize(graph))
        evaluated_graphs.extend(evaluated.graphs)
        diagnostics.limits_reached.extend(evaluated.diagnostics.limits_reached)
        diagnostics.errors.extend(evaluated.diagnostics.errors)
    return EvaluatedGraphs(graphs=evaluated_graphs, diagnostics=diagnostics)
