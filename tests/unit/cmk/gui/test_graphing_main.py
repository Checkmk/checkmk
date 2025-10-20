#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing import v1 as graphing_api
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.graphing._from_api import graphs_from_api, metrics_from_api
from cmk.gui.graphing._graph_templates import get_graph_plugin_from_id
from cmk.gui.graphing._legacy import check_metrics
from cmk.gui.graphing._metrics import get_metric_spec
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.graphing_main import _add_graphing_plugins, _load_graphing_plugins
from cmk.gui.unit_formatter import StrictPrecision


def test_add_graphing_plugins() -> None:
    _add_graphing_plugins(_load_graphing_plugins())

    idle_connections = get_metric_spec("idle_connections", metrics_from_api)
    assert idle_connections.name == "idle_connections"
    assert idle_connections.title == "Idle connections"
    assert idle_connections.unit_spec == ConvertibleUnitSpecification(
        notation=DecimalNotation(symbol=""),
        precision=StrictPrecision(digits=2),
    )
    assert idle_connections.color == "#b441f0"

    active_connections = get_metric_spec("active_connections", metrics_from_api)
    assert active_connections.name == "active_connections"
    assert active_connections.title == "Active connections"
    assert active_connections.unit_spec == ConvertibleUnitSpecification(
        notation=DecimalNotation(symbol=""),
        precision=StrictPrecision(digits=2),
    )
    assert active_connections.color == "#d28df6"

    assert "check_mk-citrix_serverload" in check_metrics
    assert check_metrics["check_mk-citrix_serverload"] == {
        "perf": {"name": "citrix_load", "scale": 0.01},
    }

    assert "check_mk-genau_fan" in check_metrics
    assert check_metrics["check_mk-genau_fan"] == {
        "rpm": {"name": "fan"},
    }

    assert "check_mk-ibm_svc_nodestats_disk_latency" in check_metrics
    assert check_metrics["check_mk-ibm_svc_nodestats_disk_latency"] == {
        "read_latency": {"scale": 0.001},
        "write_latency": {"scale": 0.001},
    }

    assert get_graph_plugin_from_id(graphs_from_api, "db_connections") == graphs_api.Graph(
        name="db_connections",
        title=graphing_api.Title("DB Connections"),
        simple_lines=[
            "active_connections",
            "idle_connections",
            metrics_api.WarningOf("active_connections"),
            metrics_api.CriticalOf("active_connections"),
        ],
    )
