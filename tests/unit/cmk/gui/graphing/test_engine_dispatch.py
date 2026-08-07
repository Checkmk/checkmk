#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Self

import pytest

from cmk.graphing_engine import (
    ConsolidationFunction,
    EvaluatedGraph,
    Graph,
    TimeRange,
)
from cmk.gui.graphing._engine_codec import community_graph_codec
from cmk.gui.graphing._engine_dispatch import (
    CommonGraphOptions,
    evaluate_built_graphs,
    evaluate_graphs,
    EvaluatedGraphs,
    graph_dispatcher_registry,
    GraphDispatcher,
    serialize_graphs,
)
from cmk.gui.graphing._engine_source import FetchDiagnostics, QueryLimitReached

_KIND = "dispatch_test"

_OPTIONS: Mapping[str, object] = {
    "consolidation_function": ConsolidationFunction.MAX,
    "time_range": TimeRange(start=0, end=60, step=10),
}


@dataclass
class _RecordingEvaluate:
    # Stands in for a graph kind's evaluation: it reports the graph it was handed back as the
    # evaluated result and as a diagnostic, so a test can tell what reached it.
    options: CommonGraphOptions
    diagnostics: FetchDiagnostics = field(default_factory=FetchDiagnostics)

    @classmethod
    def make(cls, options: Mapping[str, object]) -> Self:
        return cls(CommonGraphOptions.from_request_options(options))

    def __call__(self, graph: Graph) -> EvaluatedGraphs:
        self.diagnostics.errors.append(f"{graph.name} at step {self.options.time_range.step}")
        self.diagnostics.limits_reached.append(
            QueryLimitReached(metric_name=graph.name, max_series=1, num_series=2)
        )
        return EvaluatedGraphs(
            graphs=[
                EvaluatedGraph(
                    name=graph.name,
                    title=graph.title,
                    vertical_range=None,
                    stacks=[],
                    lines=[],
                )
            ],
            diagnostics=self.diagnostics,
        )


@pytest.fixture(name="dispatched_kind")
def _dispatched_kind() -> Iterator[None]:
    graph_dispatcher_registry.register(
        GraphDispatcher(
            kind=_KIND,
            codec=community_graph_codec(),
            make_evaluate=_RecordingEvaluate.make,
        )
    )
    try:
        yield
    finally:
        graph_dispatcher_registry.unregister(_KIND)


def _graph(name: str) -> Graph:
    return Graph(name=name, title=f"title of {name}", kind=_KIND)


@pytest.mark.usefixtures("dispatched_kind")
def test_built_graphs_evaluate_without_a_wire_form() -> None:
    # A caller that built the graphs itself hands them over as they are - the codec is for what
    # comes off the wire, not for what never left.
    evaluated = evaluate_built_graphs([_graph("a")], _OPTIONS)

    assert [graph.name for graph in evaluated.graphs] == ["a"]


@pytest.mark.usefixtures("dispatched_kind")
def test_built_and_serialized_graphs_evaluate_the_same() -> None:
    graphs = [_graph("a"), _graph("b")]

    from_built = evaluate_built_graphs(graphs, _OPTIONS)
    from_wire = evaluate_graphs(serialize_graphs(graphs), _OPTIONS)

    assert [graph.name for graph in from_built.graphs] == [graph.name for graph in from_wire.graphs]
    assert from_built.diagnostics.errors == from_wire.diagnostics.errors


@pytest.mark.usefixtures("dispatched_kind")
def test_the_diagnostics_of_every_graph_are_collected() -> None:
    # Every graph makes its own evaluation, so a hit limit only reaches the caller if the dispatch
    # gathers what each of them reported.
    evaluated = evaluate_built_graphs([_graph("a"), _graph("b")], _OPTIONS)

    assert [limit.metric_name for limit in evaluated.diagnostics.limits_reached] == ["a", "b"]


@pytest.mark.usefixtures("dispatched_kind")
def test_every_graph_is_evaluated_under_the_requested_options() -> None:
    evaluated = evaluate_built_graphs(
        [_graph("a"), _graph("b")],
        {
            "consolidation_function": ConsolidationFunction.MAX,
            "time_range": TimeRange(start=0, end=120, step=30),
        },
    )

    assert evaluated.diagnostics.errors == ["a at step 30", "b at step 30"]


@pytest.mark.usefixtures("dispatched_kind")
def test_a_graph_of_an_unregistered_kind_is_refused() -> None:
    with pytest.raises(KeyError):
        evaluate_built_graphs([Graph(name="a", title="t", kind="not_registered")], _OPTIONS)
