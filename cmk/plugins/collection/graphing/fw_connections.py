#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_fw_connections_active = metrics.Metric(
    name="fw_connections_active",
    title=Title("Active connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_fw_connections_established = metrics.Metric(
    name="fw_connections_established",
    title=Title("Established connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_fw_connections_halfclosed = metrics.Metric(
    name="fw_connections_halfclosed",
    title=Title("Half closed connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_fw_connections_halfopened = metrics.Metric(
    name="fw_connections_halfopened",
    title=Title("Half opened connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_fw_connections_passthrough = metrics.Metric(
    name="fw_connections_passthrough",
    title=Title("Unoptimized connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PINK,
)

perfometer_fw_connections_active = perfometers.Perfometer(
    name="fw_connections_active",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(200),
    ),
    segments=["fw_connections_active"],
)

graph_firewall_connections = graphs.Graph(
    name="firewall_connections",
    title=Title("Firewall connections"),
    compound_lines=[
        "fw_connections_active",
        "fw_connections_established",
        "fw_connections_halfopened",
        "fw_connections_halfclosed",
        "fw_connections_passthrough",
    ],
)
