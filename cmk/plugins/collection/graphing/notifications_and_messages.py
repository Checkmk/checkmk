#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

metric_notification_delivery_rate = metrics.Metric(
    name="notification_delivery_rate",
    title=Title("Notification delivery rate"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.GRAY,
)
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
metric_messages_in_queue = metrics.Metric(
    name="messages_in_queue",
    title=Title("Messages in queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
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

perfometer_notification_delivery_rate = perfometers.Perfometer(
    name="notification_delivery_rate",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100.0)),
    segments=["notification_delivery_rate"],
)
perfometer_messages_in_queue = perfometers.Perfometer(
    name="messages_in_queue",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(1),
    ),
    segments=["messages_in_queue"],
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

graph_messages = graphs.Graph(
    name="messages",
    title=Title("Messages"),
    simple_lines=[
        "failed_notifications",
        "delivered_notifications",
        "messages_publish",
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
