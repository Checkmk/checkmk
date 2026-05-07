#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_clients_connected = metrics.Metric(
    name="clients_connected",
    title=Title("Clients connected"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)
metric_clients_maximum = metrics.Metric(
    name="clients_maximum",
    title=Title("Clients maximum"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)
metric_clients_total = metrics.Metric(
    name="clients_total",
    title=Title("Clients total"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)
graph_mqtt_clients = graphs.Graph(
    name="mqtt_clients",
    title=Title("Clients"),
    simple_lines=[
        "clients_connected",
        "clients_maximum",
        "clients_total",
    ],
    optional=["clients_maximum"],
)
