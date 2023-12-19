#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import Color, graphs, Localizable, metrics, Unit

metric_connections_opened_received_rate = metrics.Metric(
    name="connections_opened_received_rate",
    title=Localizable("Connections opened"),
    unit=Unit.PER_SECOND,
    color=Color.PURPLE,
)

metric_subscriptions = metrics.Metric(
    name="subscriptions",
    title=Localizable("Current subscriptions"),
    unit=Unit.PER_SECOND,
    color=Color.ORANGE,
)

metric_clients_connected = metrics.Metric(
    name="clients_connected",
    title=Localizable("Clients connected"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_clients_maximum = metrics.Metric(
    name="clients_maximum",
    title=Localizable("Clients maximum"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_clients_total = metrics.Metric(
    name="clients_total",
    title=Localizable("Clients total"),
    unit=Unit.COUNT,
    color=Color.YELLOW,
)

metric_bytes_received_rate = metrics.Metric(
    name="bytes_received_rate",
    title=Localizable("Bytes received"),
    unit=Unit.BYTE_IEC_PER_SECOND,
    color=Color.GREEN,
)

metric_bytes_sent_rate = metrics.Metric(
    name="bytes_sent_rate",
    title=Localizable("Bytes sent"),
    unit=Unit.BYTE_IEC_PER_SECOND,
    color=Color.BLUE,
)

metric_messages_received_rate = metrics.Metric(
    name="messages_received_rate",
    title=Localizable("Messages received"),
    unit=Unit.PER_SECOND,
    color=Color.GREEN,
)

metric_messages_sent_rate = metrics.Metric(
    name="messages_sent_rate",
    title=Localizable("Messages sent"),
    unit=Unit.PER_SECOND,
    color=Color.BLUE,
)

metric_publish_bytes_received_rate = metrics.Metric(
    name="publish_bytes_received_rate",
    title=Localizable("PUBLISH messages: Bytes received"),
    unit=Unit.BYTE_IEC_PER_SECOND,
    color=Color.GREEN,
)

metric_publish_bytes_sent_rate = metrics.Metric(
    name="publish_bytes_sent_rate",
    title=Localizable("PUBLISH messages: Bytes sent"),
    unit=Unit.BYTE_IEC_PER_SECOND,
    color=Color.BLUE,
)

metric_publish_messages_received_rate = metrics.Metric(
    name="publish_messages_received_rate",
    title=Localizable("PUBLISH messages received"),
    unit=Unit.PER_SECOND,
    color=Color.GREEN,
)

metric_publish_messages_sent_rate = metrics.Metric(
    name="publish_messages_sent_rate",
    title=Localizable("PUBLISH messages sent"),
    unit=Unit.PER_SECOND,
    color=Color.BLUE,
)

metric_retained_messages = metrics.Metric(
    name="retained_messages",
    title=Localizable("Retained messages"),
    unit=Unit.COUNT,
    color=Color.PURPLE,
)

metric_stored_messages = metrics.Metric(
    name="stored_messages",
    title=Localizable("Stored messages"),
    unit=Unit.COUNT,
    color=Color.ORANGE,
)

metric_stored_messages_bytes = metrics.Metric(
    name="stored_messages_bytes",
    title=Localizable("Size of stored messages"),
    unit=Unit.BYTE_IEC,
    color=Color.YELLOW,
)

graph_mqtt_clients = graphs.Graph(
    name="mqtt_clients",
    title=Localizable("Clients"),
    simple_lines=[
        "clients_connected",
        "clients_maximum",
        "clients_total",
    ],
    optional=["clients_maximum"],
)

graph_bytes_transmitted = graphs.Bidirectional(
    name="bytes_transmitted",
    title=Localizable("Bytes sent/received"),
    lower=graphs.Graph(
        name="bytes_transmitted",
        title=Localizable("Bytes sent/received"),
        compound_lines=["bytes_sent_rate"],
    ),
    upper=graphs.Graph(
        name="bytes_transmitted",
        title=Localizable("Bytes sent/received"),
        compound_lines=["bytes_received_rate"],
    ),
)

graph_messages_transmitted = graphs.Bidirectional(
    name="messages_transmitted",
    title=Localizable("Messages sent/received"),
    lower=graphs.Graph(
        name="messages_transmitted",
        title=Localizable("Messages sent/received"),
        compound_lines=["messages_sent_rate"],
    ),
    upper=graphs.Graph(
        name="messages_transmitted",
        title=Localizable("Messages sent/received"),
        compound_lines=["messages_received_rate"],
    ),
)

graph_publish_bytes_transmitted = graphs.Bidirectional(
    name="publish_bytes_transmitted",
    title=Localizable("PUBLISH messages: Bytes sent/received"),
    lower=graphs.Graph(
        name="publish_bytes_transmitted",
        title=Localizable("PUBLISH messages: Bytes sent/received"),
        compound_lines=["publish_bytes_sent_rate"],
    ),
    upper=graphs.Graph(
        name="publish_bytes_transmitted",
        title=Localizable("PUBLISH messages: Bytes sent/received"),
        compound_lines=["publish_bytes_received_rate"],
    ),
)

graph_publish_messages_transmitted = graphs.Bidirectional(
    name="publish_messages_transmitted",
    title=Localizable("PUBLISH messages sent/received"),
    lower=graphs.Graph(
        name="publish_messages_transmitted",
        title=Localizable("PUBLISH messages sent/received"),
        compound_lines=["publish_messages_sent_rate"],
    ),
    upper=graphs.Graph(
        name="publish_messages_transmitted",
        title=Localizable("PUBLISH messages sent/received"),
        compound_lines=["publish_messages_received_rate"],
    ),
)
