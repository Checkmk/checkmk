#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_wifi_connection_dot11a = metrics.Metric(
    name="wifi_connection_dot11a",
    title=Title("802.dot11a"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_wifi_connection_dot11ac = metrics.Metric(
    name="wifi_connection_dot11ac",
    title=Title("802.dot11ac"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_wifi_connection_dot11b = metrics.Metric(
    name="wifi_connection_dot11b",
    title=Title("802.dot11b"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_wifi_connection_dot11g = metrics.Metric(
    name="wifi_connection_dot11g",
    title=Title("802.dot11g"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_wifi_connection_dot11n2_4 = metrics.Metric(
    name="wifi_connection_dot11n2_4",
    title=Title("802.dot11n2_4"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_wifi_connection_dot11n5 = metrics.Metric(
    name="wifi_connection_dot11n5",
    title=Title("802.dot11n5"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BROWN,
)

graph_wifi_connections = graphs.Graph(
    name="wifi_connections",
    title=Title("WiFi connection types"),
    compound_lines=[
        "wifi_connection_dot11a",
        "wifi_connection_dot11b",
        "wifi_connection_dot11g",
        "wifi_connection_dot11ac",
        "wifi_connection_dot11n2_4",
        "wifi_connection_dot11n5",
    ],
)
