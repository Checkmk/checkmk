#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_net_in_throughput = metrics.Metric(
    name="net_in_throughput",
    title=Title("Network Inbound"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_net_out_throughput = metrics.Metric(
    name="net_out_throughput",
    title=Title("Network Outbound"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)

perfometer_network_throughput = perfometers.Bidirectional(
    name="network_throughput",
    left=perfometers.Perfometer(
        name="net_in_throughput",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(9000000)),
        segments=["net_in_throughput"],
    ),
    right=perfometers.Perfometer(
        name="net_out_throughput",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(9000000)),
        segments=["net_out_throughput"],
    ),
)

graph_network_throughput = graphs.Bidirectional(
    name="network_throughput",
    title=Title("Network Throughput"),
    lower=graphs.Graph(
        name="net_in_throughput",
        title=Title("In Throughput"),
        compound_lines=["net_in_throughput"],
        simple_lines=[
            metrics.WarningOf("net_in_throughput"),
            metrics.CriticalOf("net_in_throughput"),
        ],
    ),
    upper=graphs.Graph(
        name="net_out_throughput",
        title=Title("Out Throughput"),
        compound_lines=["net_out_throughput"],
        simple_lines=[
            metrics.WarningOf("net_out_throughput"),
            metrics.CriticalOf("net_out_throughput"),
        ],
    ),
)
