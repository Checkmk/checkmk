#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_delivered_notifications = metrics.Metric(
    name="delivered_notifications",
    title=Title("Delivered notifications"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_BLUE,
)
metric_failed_notifications = metrics.Metric(
    name="failed_notifications",
    title=Title("Failed notifications"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_messages_publish = metrics.Metric(
    name="messages_publish",
    title=Title("Published messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)

graph_messages = graphs.Graph(
    name="messages",
    title=Title("Messages"),
    simple_lines=[
        "failed_notifications",
        "delivered_notifications",
        "messages_publish",
    ],
)
