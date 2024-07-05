#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_edge_tcp_allocate_requests_exceeding_port_limit = metrics.Metric(
    name="edge_tcp_allocate_requests_exceeding_port_limit",
    title=Title("A/V Edge - TCP allocate requests exceeding port limit"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_edge_udp_allocate_requests_exceeding_port_limit = metrics.Metric(
    name="edge_udp_allocate_requests_exceeding_port_limit",
    title=Title("A/V Edge - UDP allocate requests exceeding port limit"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_allocate_requests_exceeding_port_limit = graphs.Graph(
    name="allocate_requests_exceeding_port_limit",
    title=Title("Allocate requests exceeding port limit"),
    simple_lines=[
        "edge_udp_allocate_requests_exceeding_port_limit",
        "edge_tcp_allocate_requests_exceeding_port_limit",
    ],
)
