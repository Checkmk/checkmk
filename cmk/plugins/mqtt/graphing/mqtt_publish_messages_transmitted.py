#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_publish_messages_sent_rate = metrics.Metric(
    name="publish_messages_sent_rate",
    title=Title("PUBLISH messages sent"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_publish_messages_received_rate = metrics.Metric(
    name="publish_messages_received_rate",
    title=Title("PUBLISH messages received"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

graph_publish_messages_transmitted = graphs.Bidirectional(
    name="publish_messages_transmitted",
    title=Title("PUBLISH messages sent/received"),
    lower=graphs.Graph(
        name="publish_messages_transmitted",
        title=Title("PUBLISH messages sent/received"),
        compound_lines=["publish_messages_sent_rate"],
    ),
    upper=graphs.Graph(
        name="publish_messages_transmitted",
        title=Title("PUBLISH messages sent/received"),
        compound_lines=["publish_messages_received_rate"],
    ),
)
