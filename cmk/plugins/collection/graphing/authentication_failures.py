#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_edge_tcp_failed_auth = metrics.Metric(
    name="edge_tcp_failed_auth",
    title=Title("A/V Edge - TCP authentication failures"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_edge_udp_failed_auth = metrics.Metric(
    name="edge_udp_failed_auth",
    title=Title("UDP authentication failures"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_authentication_failures = graphs.Graph(
    name="authentication_failures",
    title=Title("Authentication failures"),
    simple_lines=[
        "edge_udp_failed_auth",
        "edge_tcp_failed_auth",
    ],
)
