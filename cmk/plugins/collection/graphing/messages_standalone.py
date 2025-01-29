#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_messages = metrics.Metric(
    name="messages",
    title=Title("Messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_msgs_avg = metrics.Metric(
    name="msgs_avg",
    title=Title("Average number of messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_messages_rate = metrics.Metric(
    name="messages_rate",
    title=Title("Message Rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_messages_ready = metrics.Metric(
    name="messages_ready",
    title=Title("Ready messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_messages_unacknowledged = metrics.Metric(
    name="messages_unacknowledged",
    title=Title("Unacknowledged messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_messages_publish_rate = metrics.Metric(
    name="messages_publish_rate",
    title=Title("Published message rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_messages_deliver = metrics.Metric(
    name="messages_deliver",
    title=Title("Delivered messages"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_messages_deliver_rate = metrics.Metric(
    name="messages_deliver_rate",
    title=Title("Delivered message rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)
