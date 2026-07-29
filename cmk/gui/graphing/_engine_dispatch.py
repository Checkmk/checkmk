#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from cmk.ccc.plugin_registry import Registry
from cmk.graphing_engine import ConsolidationFunction, EvaluatedGraph, Graph, TimeRange

from ._engine_rrd import FetchDiagnostics
from ._engine_serialization import (
    consolidation_function_of,
    ensure_type,
    GraphCodec,
    time_range_of,
)
from ._graph_specification import GraphSpecification


@dataclass(frozen=True)
class BuiltGraph:
    # An engine graph bundled with the legacy specification it can be added to (dashboard, report,
    # graph collection, custom graph). ``specification`` is None for graph kinds that offer no "Add
    # to" action; otherwise it carries the concrete per-graph specification the add-to endpoints
    # replay.
    graph: Graph
    specification: GraphSpecification | None


@dataclass(frozen=True, kw_only=True)
class CommonGraphOptions:
    # The options common to every graph type's evaluation. A graph type only defines its own options
    # dataclass when it needs more than these (e.g. combined graphs add their combination mode).
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


class DispatchedEvaluate(Protocol):
    # A graph type's evaluation, on the graph its deserialization produced.
    def __call__(
        self,
        *,
        graph: Graph,
        options: Mapping[str, object],
    ) -> EvaluatedGraphs: ...


@dataclass(frozen=True)
class EngineGraphDispatcher:
    kind: str
    codec: GraphCodec
    evaluate: DispatchedEvaluate

    def serialize(self, graph: Graph) -> Mapping[str, object]:
        return self.codec.serialize_graph(graph)

    def deserialize(self, graph: Mapping[str, object]) -> Graph:
        return self.codec.deserialize_graph(graph)


class EngineGraphDispatcherRegistry(Registry[EngineGraphDispatcher]):
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
    # The definition may hold graphs of different kinds, but they share the options of one request.
    for serialized in ensure_type(internal["graphs"], list):
        graph = ensure_type(serialized, dict)
        dispatcher = engine_graph_dispatcher_registry[ensure_type(graph["kind"], str)]
        evaluated = dispatcher.evaluate(graph=dispatcher.deserialize(graph), options=options)
        evaluated_graphs.extend(evaluated.graphs)
        diagnostics.limits_reached.extend(evaluated.diagnostics.limits_reached)
        diagnostics.errors.extend(evaluated.diagnostics.errors)
    return EvaluatedGraphs(graphs=evaluated_graphs, diagnostics=diagnostics)
