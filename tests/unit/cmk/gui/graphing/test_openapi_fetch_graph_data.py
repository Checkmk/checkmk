#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

import pytest

from livestatus import MKLivestatusSocketError

from cmk.graphing_engine import (
    AutoPrecision,
    ConsolidationFunction,
    Curve,
    CurveAttributes,
    DecimalNotation,
    EvaluatedGraph,
    FetchedData,
    Graph,
    HostName,
    Line,
    Metric,
    MetricName,
    PerformanceData,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceName,
    TimeRange,
    TimeSeries,
    Unit,
)
from cmk.gui.graphing._engine_dispatch import (
    CommonGraphOptions,
    EvaluatedGraphs,
    serialize_graphs,
)
from cmk.gui.graphing._engine_rrd import FetchDiagnostics, QueryLimitReached
from cmk.gui.graphing._engine_template_graphs import evaluate_template_graphs
from cmk.gui.graphing.openapi import fetch_graph_data as fetch_graph_data_module
from cmk.gui.graphing.openapi._serialize import api_consolidation_to_engine, evaluated_to_response
from cmk.gui.graphing.openapi.fetch_graph_data import fetch_graph_data_v1
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
    assert api_consolidation_to_engine(value) == expected


def test_evaluated_to_response_surfaces_fetch_diagnostics() -> None:
    # A hit series cap becomes a warning; a per-query fetch error becomes an error entry.
    response = evaluated_to_response(
        EvaluatedGraph(name="g", title="t", vertical_range=None, stacks=[], lines=[]),
        fallback_time_range=TimeRange(start=0, end=60, step=10),
        diagnostics=FetchDiagnostics(
            limits_reached=[QueryLimitReached(metric_name="cpu", max_series=100, num_series=100)],
            errors=["metric backend unavailable"],
        ),
    )
    assert response.errors == ["metric backend unavailable"]
    assert len(response.warnings) == 1
    assert "cpu" in response.warnings[0]


def test_evaluated_to_response_has_no_diagnostics_by_default() -> None:
    response = evaluated_to_response(
        EvaluatedGraph(name="g", title="t", vertical_range=None, stacks=[], lines=[]),
        fallback_time_range=TimeRange(start=0, end=60, step=10),
        diagnostics=FetchDiagnostics(),
    )
    assert response.warnings == []
    assert response.errors == []


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_empty_graph_runs_end_to_end() -> None:
    # An empty graph has no metrics, so the livestatus-backed RRD source is never queried. The handler
    # therefore runs end to end (evaluate_graphs -> evaluate_template_graphs -> evaluated_to_response)
    # and returns an empty, fallback-ranged response -- guarding the real wiring without a livestatus
    # fixture.
    graph = Graph(name="g", title="t", kind="template")
    request = GraphFetchRequest(
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
        internal={"garbage": "data"},
        requested_time_range=ApiTimeRange(start=0, end=60, step=10),
        consolidation_function="avg",
    )
    with pytest.raises(ProblemException) as exc_info:
        fetch_graph_data_v1(request)
    assert exc_info.value.code == 500
    assert "Failed to evaluate graph" in exc_info.value.detail


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_unknown_graph_kind_raises_500() -> None:
    # Routing is by the graph's own kind; an unregistered kind has no dispatcher and fails evaluation.
    request = GraphFetchRequest(
        internal={"graphs": [{"kind": "does-not-exist"}]},
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
    def _raise(_graphs: object, _options: object) -> None:
        raise MKLivestatusSocketError("connection refused")

    monkeypatch.setattr(fetch_graph_data_module, "evaluate_graphs", _raise)
    request = GraphFetchRequest(
        internal=serialize_graphs([Graph(name="g", title="t", kind="template")]),
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
        Graph(name="g1", title="t1", kind="template"),
        Graph(name="g2", title="t2", kind="template"),
    ]
    request = GraphFetchRequest(
        internal=serialize_graphs(graphs),
        requested_time_range=ApiTimeRange(start=0, end=60, step=10),
        consolidation_function="avg",
    )
    with pytest.raises(ProblemException) as exc_info:
        fetch_graph_data_v1(request)
    assert exc_info.value.code == 500
    assert "Expected exactly one graph" in exc_info.value.detail
    assert "got 2" in exc_info.value.detail


def _capture_request(
    monkeypatch: pytest.MonkeyPatch, captured: dict[str, Mapping[str, object]]
) -> None:
    def _capture(
        _graphs: Sequence[Mapping[str, object]], options: Mapping[str, object]
    ) -> EvaluatedGraphs:
        captured["options"] = options
        return EvaluatedGraphs(
            graphs=[EvaluatedGraph(name="g", title="t", vertical_range=None, stacks=[], lines=[])],
            diagnostics=FetchDiagnostics(),
        )

    monkeypatch.setattr(fetch_graph_data_module, "evaluate_graphs", _capture)


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_passes_combination_mode_into_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Mapping[str, object]] = {}
    _capture_request(monkeypatch, captured)
    fetch_graph_data_v1(
        GraphFetchRequest(
            internal=serialize_graphs([Graph(name="g", title="t", kind="template")]),
            requested_time_range=ApiTimeRange(start=0, end=60, step=10),
            consolidation_function="avg",
            combination_mode="stacked",
        )
    )
    assert captured["options"]["combination_mode"] == "stacked"


@pytest.mark.usefixtures("load_config")
def test_fetch_graph_data_omits_combination_mode_when_not_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Mapping[str, object]] = {}
    _capture_request(monkeypatch, captured)
    fetch_graph_data_v1(
        GraphFetchRequest(
            internal=serialize_graphs([Graph(name="g", title="t", kind="template")]),
            requested_time_range=ApiTimeRange(start=0, end=60, step=10),
            consolidation_function="avg",
        )
    )
    assert "combination_mode" not in captured["options"]


def test_evaluated_to_response_carries_the_lines_and_the_scalars() -> None:
    unit = Unit(notation=DecimalNotation("X"), precision=AutoPrecision(2))
    metric = RRDMetric(
        host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("m")
    )
    graph = Graph(
        name="g",
        title="My Graph",
        kind="template",
        lines=[
            Line(
                curve=Curve(
                    quantity=metric,
                    attributes=CurveAttributes(title="Line", unit=unit, color="#0000ff"),
                ),
                inverse=False,
            )
        ],
        rules=[
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=metric, scalar_kind=ScalarKind.WARNING),
                    attributes=CurveAttributes(title="Warning", unit=unit, color="#ffcc00"),
                ),
                inverse=False,
            )
        ],
    )
    time_range = TimeRange(start=0, end=30, step=10)

    def _fetch_data(
        metrics: Sequence[Metric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[Metric, Sequence[FetchedData]]:
        return {
            rrd_metric: [
                FetchedData(
                    performance_data=PerformanceData(value=5.0, warning=80.0),
                    time_series=TimeSeries(time_range=time_range, values=[1.0, None, 3.0]),
                )
            ]
            for rrd_metric in metrics
            if isinstance(rrd_metric, RRDMetric)
        }

    [evaluated] = evaluate_template_graphs(
        graphs=[graph],
        options=CommonGraphOptions(
            consolidation_function=ConsolidationFunction.AVERAGE, time_range=time_range
        ),
        fetch_data=_fetch_data,
    )
    response = evaluated_to_response(
        evaluated, fallback_time_range=time_range, diagnostics=FetchDiagnostics()
    )

    [line] = response.metrics
    assert line.metadata.title == "Line"
    assert line.metadata.color == "#0000ff"
    assert line.data_points == [1.0, None, 3.0]
    [horizontal_line] = response.horizontal_lines
    assert (horizontal_line.value, horizontal_line.color) == (80.0, "#ffcc00")
