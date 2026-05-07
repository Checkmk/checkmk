#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_messages_sent_rate = metrics.Metric(
    name="messages_sent_rate",
    title=Title("Messages sent"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_messages_received_rate = metrics.Metric(
    name="messages_received_rate",
    title=Title("Messages received"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_messages_transmitted = graphs.Bidirectional(
    name="messages_transmitted",
    title=Title("Messages sent/received"),
    lower=graphs.Graph(
        name="messages_transmitted",
        title=Title("Messages sent/received"),
        compound_lines=["messages_sent_rate"],
    ),
    upper=graphs.Graph(
        name="messages_transmitted",
        title=Title("Messages sent/received"),
        compound_lines=["messages_received_rate"],
    ),
)
