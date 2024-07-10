#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_client_req_rate = metrics.Metric(
    name="varnish_client_req_rate",
    title=Title("Client requests received"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_client_conn_rate = metrics.Metric(
    name="varnish_client_conn_rate",
    title=Title("Client connections accepted"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_client_drop_rate = metrics.Metric(
    name="varnish_client_drop_rate",
    title=Title("Connections dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_varnish_client_drop_late_rate = metrics.Metric(
    name="varnish_client_drop_late_rate",
    title=Title("Connection dropped late"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

graph_varnish_clients = graphs.Graph(
    name="varnish_clients",
    title=Title("Varnish Clients"),
    simple_lines=[
        "varnish_client_req_rate",
        "varnish_client_conn_rate",
        "varnish_client_drop_rate",
        "varnish_client_drop_late_rate",
    ],
)
