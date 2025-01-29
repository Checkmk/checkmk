#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_net_data_recv = metrics.Metric(
    name="net_data_recv",
    title=Title("Net data received"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_net_data_sent = metrics.Metric(
    name="net_data_sent",
    title=Title("Net data sent"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_net_data_recv_net_data_sent = perfometers.Bidirectional(
    name="net_data_recv_net_data_sent",
    left=perfometers.Perfometer(
        name="net_data_recv",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(9000000),
        ),
        segments=["net_data_recv"],
    ),
    right=perfometers.Perfometer(
        name="net_data_sent",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(9000000),
        ),
        segments=["net_data_sent"],
    ),
)

graph_net_data_traffic = graphs.Graph(
    name="net_data_traffic",
    title=Title("Net data traffic"),
    compound_lines=[
        "net_data_recv",
        "net_data_sent",
    ],
)
