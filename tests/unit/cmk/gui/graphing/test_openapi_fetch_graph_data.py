#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from livestatus import MKLivestatusSocketError

from cmk.graphing_engine import ConsolidationFunction, Graph
from cmk.gui.graphing._engine_serialization import serialize_graphs
from cmk.gui.graphing.openapi import fetch_graph_data as fetch_graph_data_module
from cmk.gui.graphing.openapi.fetch_graph_data import _consolidation_function, fetch_graph_data_v1
from cmk.gui.graphing.openapi.models import ApiTimeRange, GraphFetchRequest
from cmk.gui.openapi.utils import ProblemException


@pytest.mark.parametrize(
    "value, expected",
    [
        ("min", ConsolidationFunction.MIN),
        ("max", ConsolidationFunction.MAX),
        ("avg", ConsolidationFunction.AVERAGE),
    ],
)
def test_consolidation_function_mapping(
    value: Literal["min", "max", "avg"], expected: ConsolidationFunction
) -> None:
    assert _consolidation_function(value) == expected


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_empty_graph_runs_end_to_end() -> None:
    # An empty graph has no metrics, so the livestatus-backed RRD source is never queried. The handler
    # therefore runs end to end (evaluate_graphs -> evaluate_template_graphs -> evaluated_to_response)
    # and returns an empty, fallback-ranged response -- guarding the real wiring without a livestatus
    # fixture.
    graph = Graph(name="g", title="t", graph_type="template")
    request = GraphFetchRequest(
        graph_type="template",
        internal=serialize_graphs([graph]),
        requested_time_range=ApiTimeRange(start=0, end=60, step=10),
        consolidation_function="avg",
    )
    response = fetch_graph_data_v1(request)
    assert response.metrics == []
    assert response.horizontal_lines == []
    assert response.time_range == ApiTimeRange(start=0, end=60, step=10)


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_invalid_internal_raises_500() -> None:
    request = GraphFetchRequest(
        graph_type="template",
        internal={"garbage": "data"},
        requested_time_range=ApiTimeRange(start=0, end=60, step=10),
        consolidation_function="avg",
    )
    with pytest.raises(ProblemException) as exc_info:
        fetch_graph_data_v1(request)
    assert exc_info.value.code == 500
    assert "Failed to evaluate graph" in exc_info.value.detail


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_unknown_graph_type_raises_500() -> None:
    request = GraphFetchRequest(
        graph_type="does-not-exist",
        internal=serialize_graphs([Graph(name="g", title="t", graph_type="template")]),
        requested_time_range=ApiTimeRange(start=0, end=60, step=10),
        consolidation_function="avg",
    )
    with pytest.raises(ProblemException) as exc_info:
        fetch_graph_data_v1(request)
    assert exc_info.value.code == 500


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_livestatus_failure_raises_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(_request: object) -> None:
        raise MKLivestatusSocketError("connection refused")

    monkeypatch.setattr(fetch_graph_data_module, "evaluate_graphs", _raise)
    request = GraphFetchRequest(
        graph_type="template",
        internal=serialize_graphs([Graph(name="g", title="t", graph_type="template")]),
        requested_time_range=ApiTimeRange(start=0, end=60, step=10),
        consolidation_function="avg",
    )
    with pytest.raises(ProblemException) as exc_info:
        fetch_graph_data_v1(request)
    assert exc_info.value.code == 503
    assert "connection refused" in exc_info.value.detail


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_multiple_internal_graphs_raises_500() -> None:
    graphs = [
        Graph(name="g1", title="t1", graph_type="template"),
        Graph(name="g2", title="t2", graph_type="template"),
    ]
    request = GraphFetchRequest(
        graph_type="template",
        internal=serialize_graphs(graphs),
        requested_time_range=ApiTimeRange(start=0, end=60, step=10),
        consolidation_function="avg",
    )
    with pytest.raises(ProblemException) as exc_info:
        fetch_graph_data_v1(request)
    assert exc_info.value.code == 500
    assert "Expected exactly one graph" in exc_info.value.detail
    assert "got 2" in exc_info.value.detail
