#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

metric_connections_opened_received_rate = metrics.Metric(
    name="connections_opened_received_rate",
    title=Title("Connections opened"),
    unit=metrics.Unit.PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_subscriptions = metrics.Metric(
    name="subscriptions",
    title=Title("Current subscriptions"),
    unit=metrics.Unit.PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_clients_connected = metrics.Metric(
    name="clients_connected",
    title=Title("Clients connected"),
    unit=metrics.Unit.COUNT,
    color=metrics.Color.PURPLE,
)

metric_clients_maximum = metrics.Metric(
    name="clients_maximum",
    title=Title("Clients maximum"),
    unit=metrics.Unit.COUNT,
    color=metrics.Color.ORANGE,
)

metric_clients_total = metrics.Metric(
    name="clients_total",
    title=Title("Clients total"),
    unit=metrics.Unit.COUNT,
    color=metrics.Color.YELLOW,
)

metric_bytes_received_rate = metrics.Metric(
    name="bytes_received_rate",
    title=Title("Bytes received"),
    unit=metrics.Unit.BYTES_IEC_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_bytes_sent_rate = metrics.Metric(
    name="bytes_sent_rate",
    title=Title("Bytes sent"),
    unit=metrics.Unit.BYTES_IEC_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_messages_received_rate = metrics.Metric(
    name="messages_received_rate",
    title=Title("Messages received"),
    unit=metrics.Unit.PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_messages_sent_rate = metrics.Metric(
    name="messages_sent_rate",
    title=Title("Messages sent"),
    unit=metrics.Unit.PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_publish_bytes_received_rate = metrics.Metric(
    name="publish_bytes_received_rate",
    title=Title("PUBLISH messages: Bytes received"),
    unit=metrics.Unit.BYTES_IEC_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_publish_bytes_sent_rate = metrics.Metric(
    name="publish_bytes_sent_rate",
    title=Title("PUBLISH messages: Bytes sent"),
    unit=metrics.Unit.BYTES_IEC_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_publish_messages_received_rate = metrics.Metric(
    name="publish_messages_received_rate",
    title=Title("PUBLISH messages received"),
    unit=metrics.Unit.PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_publish_messages_sent_rate = metrics.Metric(
    name="publish_messages_sent_rate",
    title=Title("PUBLISH messages sent"),
    unit=metrics.Unit.PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_retained_messages = metrics.Metric(
    name="retained_messages",
    title=Title("Retained messages"),
    unit=metrics.Unit.COUNT,
    color=metrics.Color.PURPLE,
)

metric_stored_messages = metrics.Metric(
    name="stored_messages",
    title=Title("Stored messages"),
    unit=metrics.Unit.COUNT,
    color=metrics.Color.ORANGE,
)

metric_stored_messages_bytes = metrics.Metric(
    name="stored_messages_bytes",
    title=Title("Size of stored messages"),
    unit=metrics.Unit.BYTE_IEC,
    color=metrics.Color.YELLOW,
)

graph_mqtt_clients = graphs.Graph(
    name="mqtt_clients",
    title=Title("Clients"),
    simple_lines=[
        "clients_connected",
        "clients_maximum",
        "clients_total",
    ],
    optional=["clients_maximum"],
)

graph_bytes_transmitted = graphs.Bidirectional(
    name="bytes_transmitted",
    title=Title("Bytes sent/received"),
    lower=graphs.Graph(
        name="bytes_transmitted",
        title=Title("Bytes sent/received"),
        compound_lines=["bytes_sent_rate"],
    ),
    upper=graphs.Graph(
        name="bytes_transmitted",
        title=Title("Bytes sent/received"),
        compound_lines=["bytes_received_rate"],
    ),
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

graph_publish_bytes_transmitted = graphs.Bidirectional(
    name="publish_bytes_transmitted",
    title=Title("PUBLISH messages: Bytes sent/received"),
    lower=graphs.Graph(
        name="publish_bytes_transmitted",
        title=Title("PUBLISH messages: Bytes sent/received"),
        compound_lines=["publish_bytes_sent_rate"],
    ),
    upper=graphs.Graph(
        name="publish_bytes_transmitted",
        title=Title("PUBLISH messages: Bytes sent/received"),
        compound_lines=["publish_bytes_received_rate"],
    ),
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
