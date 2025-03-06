#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._formatter import StrictPrecision
from cmk.gui.graphing._from_api import metrics_from_api
from cmk.gui.graphing._graph_templates import get_graph_template_from_id, GraphTemplate
from cmk.gui.graphing._legacy import check_metrics
from cmk.gui.graphing._metric_expression import CriticalOf, Metric, MetricExpression, WarningOf
from cmk.gui.graphing._metrics import get_metric_spec
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation
from cmk.gui.graphing_main import _add_graphing_plugins, _load_graphing_plugins


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

    graph_template = get_graph_template_from_id("db_connections", metrics_from_api)
    assert graph_template == GraphTemplate(
        id="db_connections",
        title="DB Connections",
        scalars=[
            MetricExpression(
                WarningOf(Metric("active_connections")),
                line_type="line",
                title="Warning of Active connections",
            ),
            MetricExpression(
                CriticalOf(Metric("active_connections")),
                line_type="line",
                title="Critical of Active connections",
            ),
        ],
        conflicting_metrics=(),
        optional_metrics=(),
        consolidation_function=None,
        range=None,
        omit_zero_metrics=False,
        metrics=[
            MetricExpression(
                Metric("active_connections"),
                line_type="line",
                title="Active connections",
            ),
            MetricExpression(
                Metric("idle_connections"),
                line_type="line",
                title="Idle connections",
            ),
        ],
    )
