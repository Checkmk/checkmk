#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.graphing_engine import Graph
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing._engine_rrd import EngineRRDFetchMetricNames
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.gui.graphing.openapi import discover_template_graphs as discover_module
from cmk.livestatus_client import MKLivestatusSocketError
from tests.testlib.rest_api_client import ClientRegistry


def _fake_build(graphs: Sequence[Graph]) -> Callable[..., Sequence[Graph]]:
    def _build(specification: TemplateGraphSpecification, **_kwargs: object) -> Sequence[Graph]:
        graph_id = specification.graph_id
        if graph_id is not None:
            return [
                graph
                for graph in graphs
                if graph.name == graph_id or graph.name == graph_id.removeprefix("METRIC_")
            ]
        return graphs

    return _build


def test_discover_template_graphs_emits_fetchable_graphs(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        discover_module,
        "build_template_graphs",
        _fake_build([Graph(name="g", title="t", kind="template")]),
    )
    resp = clients.Graph.discover_template_graphs(
        hostname="my-host", service_description="CPU load"
    )
    [graph] = resp.json["graphs"]
    assert graph["title"] == "t"

    # The graph's opaque definition feeds straight into the fetch_data action.
    fetch_resp = clients.Graph.fetch_data(
        internal=json.loads(graph["internal"]),
        requested_time_range={"start": 0, "end": 60, "step": 10},
        consolidation_function="max",
    )
    assert fetch_resp.json["metrics"] == []


def test_discover_template_graphs_passes_the_specification_to_the_fetch(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def _build(specification: TemplateGraphSpecification, **kwargs: object) -> Sequence[Graph]:
        captured["specification"] = specification
        captured.update(kwargs)
        return [Graph(name="g", title="t", kind="template")]

    monkeypatch.setattr(discover_module, "build_template_graphs", _build)

    clients.Graph.discover_template_graphs(hostname="my-host", service_description="CPU load")
    assert captured["specification"] == TemplateGraphSpecification(
        site=None,
        host_name=HostName("my-host"),
        service_description="CPU load",
        graph_id=None,
    )
    assert isinstance(captured["fetch_metric_names"], EngineRRDFetchMetricNames)


def test_discover_template_graphs_filters_by_graph_id(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        discover_module,
        "build_template_graphs",
        _fake_build(
            [
                Graph(name="cpu_load", title="CPU load", kind="template"),
                Graph(name="active_sessions", title="Active sessions", kind="template"),
            ]
        ),
    )
    # The legacy "METRIC_<name>" id addresses the engine's single-metric fallback graph "<name>".
    for graph_id in ("active_sessions", "METRIC_active_sessions"):
        resp = clients.Graph.discover_template_graphs(
            hostname="my-host", service_description="CPU load", graph_id=graph_id
        )
        [graph] = resp.json["graphs"]
        assert graph["title"] == "Active sessions"


def test_discover_template_graphs_unknown_graph_id_is_empty_state(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        discover_module,
        "build_template_graphs",
        _fake_build([Graph(name="cpu_load", title="CPU load", kind="template")]),
    )
    resp = clients.Graph.discover_template_graphs(
        hostname="my-host",
        service_description="CPU load",
        graph_id="does_not_exist",
    )
    assert resp.json["graphs"] == []
    assert "no matching template graphs" in resp.json["no_data_message"]


def test_discover_template_graphs_no_graphs_is_empty_state(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(discover_module, "build_template_graphs", _fake_build([]))
    resp = clients.Graph.discover_template_graphs(
        hostname="my-host", service_description="CPU load"
    )
    assert resp.json["graphs"] == []
    assert "no matching template graphs" in resp.json["no_data_message"]


def test_discover_template_graphs_missing_data_is_empty_state(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_args: object, **_kwargs: object) -> Sequence[Graph]:
        raise MKMissingDataError("As soon as you add your Checkmk server ...")

    monkeypatch.setattr(discover_module, "build_template_graphs", _raise)
    resp = clients.Graph.discover_template_graphs(
        hostname="my-host", service_description="CPU load"
    )
    assert resp.json["graphs"] == []
    assert resp.json["no_data_message"] == "As soon as you add your Checkmk server ..."


def test_discover_template_graphs_livestatus_failure_is_503(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_args: object, **_kwargs: object) -> Sequence[Graph]:
        raise MKLivestatusSocketError("connection refused")

    monkeypatch.setattr(discover_module, "build_template_graphs", _raise)
    resp = clients.Graph.discover_template_graphs(
        hostname="my-host", service_description="CPU load", expect_ok=False
    )
    assert resp.status_code == 503
    assert "connection refused" in resp.json["detail"]


def test_discover_template_graphs_invalid_hostname_is_400(clients: ClientRegistry) -> None:
    resp = clients.Graph.discover_template_graphs(
        hostname="not a valid host name",
        service_description="CPU load",
        expect_ok=False,
    )
    assert resp.status_code == 400
