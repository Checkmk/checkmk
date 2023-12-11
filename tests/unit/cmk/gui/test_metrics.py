#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._expression import CriticalOf, Metric, WarningOf
from cmk.gui.graphing._loader import load_graphing_plugins
from cmk.gui.graphing._utils import (
    add_graphing_plugins,
    check_metrics,
    graph_templates_internal,
    GraphTemplate,
    metric_info,
    MetricDefinition,
    ScalarDefinition,
)


def test_add_graphing_plugins() -> None:
    add_graphing_plugins(load_graphing_plugins())

    assert "idle_connections" in metric_info
    assert metric_info["idle_connections"] == {
        "title": "Idle connections",
        "unit": "COUNT",
        "color": "#5200a3",
    }

    assert "active_connections" in metric_info
    assert metric_info["active_connections"] == {
        "title": "Active connections",
        "unit": "COUNT",
        "color": "#7f00ff",
    }

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

    graph_templates = graph_templates_internal()
    assert "db_connections" in graph_templates
    assert graph_templates["db_connections"] == GraphTemplate(
        id="db_connections",
        title="DB Connections",
        scalars=[
            ScalarDefinition(
                WarningOf(Metric("active_connections")),
                "Active connections",
            ),
            ScalarDefinition(
                CriticalOf(Metric("active_connections")),
                "Active connections",
            ),
        ],
        conflicting_metrics=[],
        optional_metrics=[],
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
