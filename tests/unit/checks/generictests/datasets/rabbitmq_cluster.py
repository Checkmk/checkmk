#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "rabbitmq_cluster"

info = [
    [
        '{"cluster_name": "rabbit@my-rabbit", "message_stats": {"confirm": 0, "confirm_details": {"rate": 0.0}, "disk_reads": 0, "disk_reads_details": {"rate": 0.0}, "disk_writes": 0, "disk_writes_details": {"rate": 0.0}, "drop_unroutable": 0, "drop_unroutable_details": {"rate": 0.0}, "publish": 2, "publish_details": {"rate": 0.0}, "return_unroutable": 0, "return_unroutable_details": {"rate": 0.0}}, "churn_rates": {"channel_closed": 2, "channel_closed_details": {"rate": 0.0}, "channel_created": 2, "channel_created_details": {"rate": 0.0}, "connection_closed": 10, "connection_closed_details": {"rate": 0.0}, "connection_created": 10, "connection_created_details": {"rate": 0.0}, "queue_created": 1, "queue_created_details": {"rate": 0.0}, "queue_declared": 1, "queue_declared_details": {"rate": 0.0}, "queue_deleted": 0, "queue_deleted_details": {"rate": 0.0}}, "queue_totals": {"messages": 2, "messages_details": {"rate": 0.0}, "messages_ready": 2, "messages_ready_details": {"rate": 0.0}, "messages_unacknowledged": 0, "messages_unacknowledged_details": {"rate": 0.0}}, "object_totals": {"channels": 0, "connections": 0, "consumers": 0, "exchanges": 7, "queues": 1}}'
    ]
]

discovery = {"": [(None, {})], "messages": [(None, {})], "stats": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Cluster name: rabbit@my-rabbit", []),
                (0, "Rabbitmq version: None", []),
                (0, "Erlang version: None", []),
            ],
        )
    ],
    "messages": [
        (
            None,
            {},
            [
                (0, "Total number of messages: 2", [("messages", 2, None, None, None, None)]),
                (0, "Rate: 0.0 1/s", [("messages_rate", 0.0, None, None, None, None)]),
                (0, "Messages ready: 2", [("messages_ready", 2, None, None, None, None)]),
                (
                    0,
                    "Messages unacknowledged: 0",
                    [("messages_unacknowledged", 0, None, None, None, None)],
                ),
                (0, "Messages published: 2", [("messages_publish", 2, None, None, None, None)]),
                (0, "Rate: 0.0 1/s", [("messages_publish_rate", 0.0, None, None, None, None)]),
                (0, "Messages delivered: 0", [("messages_deliver", 0, None, None, None, None)]),
                (0, "Rate: 0.0 1/s", [("messages_deliver_rate", 0.0, None, None, None, None)]),
            ],
        )
    ],
    "stats": [
        (
            None,
            {},
            [
                (0, "Channels: 0", [("channels", 0, None, None, None, None)]),
                (0, "Connections: 0", [("connections", 0, None, None, None, None)]),
                (0, "Consumers: 0", [("consumers", 0, None, None, None, None)]),
                (0, "Exchanges: 7", [("exchanges", 7, None, None, None, None)]),
                (0, "Queues: 1", [("queues", 1, None, None, None, None)]),
            ],
        )
    ],
}
