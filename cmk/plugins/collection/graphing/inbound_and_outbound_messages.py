#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_messages_inbound = metrics.Metric(
    name="messages_inbound",
    title=Title("Inbound messages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_messages_outbound = metrics.Metric(
    name="messages_outbound",
    title=Title("Outbound messages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

perfometer_inbound_and_outbound_messages = perfometers.Perfometer(
    name="inbound_and_outbound_messages",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(200),
    ),
    segments=[
        metrics.Sum(
            Title(""),
            metrics.Color.GRAY,
            [
                "messages_inbound",
                "messages_outbound",
            ],
        )
    ],
)

graph_inbound_and_outbound_messages = graphs.Graph(
    name="inbound_and_outbound_messages",
    title=Title("Inbound and Outbound Messages"),
    compound_lines=[
        "messages_outbound",
        "messages_inbound",
    ],
)
