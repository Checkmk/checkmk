#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_average_message_rate = metrics.Metric(
    name="average_message_rate",
    title=Title("Incoming messages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_average_drop_rate = metrics.Metric(
    name="average_drop_rate",
    title=Title("Dropped messages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

graph_message_processing = graphs.Graph(
    name="message_processing",
    title=Title("Message processing"),
    simple_lines=[
        "average_message_rate",
        "average_drop_rate",
    ],
)
