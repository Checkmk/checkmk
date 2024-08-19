#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._expression import CriticalOf, Metric, WarningOf
from cmk.gui.graphing._graph_templates import (
    get_graph_template,
    GraphTemplate,
    MetricDefinition,
    ScalarDefinition,
)
from cmk.gui.graphing._legacy import check_metrics
from cmk.gui.graphing._metrics import get_metric_spec
from cmk.gui.metrics import _add_graphing_plugins, _load_graphing_plugins


def test_add_graphing_plugins() -> None:
    _add_graphing_plugins(_load_graphing_plugins())

    idle_connections = get_metric_spec("idle_connections")
    assert idle_connections.name == "idle_connections"
    assert idle_connections.title == "Idle connections"
    assert idle_connections.unit_info.id == "DecimalNotation__StrictPrecision_2"
    assert idle_connections.color == "#7814a0"

    active_connections = get_metric_spec("active_connections")
    assert active_connections.name == "active_connections"
    assert active_connections.title == "Active connections"
    assert active_connections.unit_info.id == "DecimalNotation__StrictPrecision_2"
    assert active_connections.color == "#b441f0"

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

    graph_template = get_graph_template("db_connections")
    assert graph_template == GraphTemplate(
        id="db_connections",
        title="DB Connections",
        scalars=[
            ScalarDefinition(
                WarningOf(Metric("active_connections")),
                "Warning of Active connections",
            ),
            ScalarDefinition(
                CriticalOf(Metric("active_connections")),
                "Critical of Active connections",
            ),
        ],
        conflicting_metrics=(),
        optional_metrics=(),
        consolidation_function=None,
        range=None,
        omit_zero_metrics=False,
        metrics=[
            MetricDefinition(
                Metric("active_connections"),
                "line",
                "Active connections",
            ),
            MetricDefinition(
                Metric("idle_connections"),
                "line",
                "Idle connections",
            ),
        ],
    )
