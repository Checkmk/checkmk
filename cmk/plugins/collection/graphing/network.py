#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.SINotation("B/s"))
UNIT_BYTES_PER_REQUEST = metrics.Unit(metrics.SINotation("B/req"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_data_transfer_rate = metrics.Metric(
    name="data_transfer_rate",
    title=Title("Data transfer rate"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)

metric_request_transfer_rate = metrics.Metric(
    name="request_transfer_rate",
    title=Title("Request transfer rate"),
    unit=UNIT_BYTES_PER_REQUEST,
    color=metrics.Color.LIGHT_GREEN,
)

metric_active_connections = metrics.Metric(
    name="active_connections",
    title=Title("Active connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_idle_connections = metrics.Metric(
    name="idle_connections",
    title=Title("Idle connections"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

graph_db_connections = graphs.Graph(
    name="db_connections",
    title=Title("DB Connections"),
    simple_lines=[
        "active_connections",
        "idle_connections",
        metrics.WarningOf("active_connections"),
        metrics.CriticalOf("active_connections"),
    ],
)
