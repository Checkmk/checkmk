#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<rabbitmq_queues>>>
# {"memory": 14332, "message_stats": {"publish": 1, "publish_details": {"rate":
# 0.0}}, "messages": 1, "messages_ready": 1, "messages_unacknowledged": 0,
# "name": "my_queue2", "node": "rabbit@my-rabbit", "state": "running", "type":
# "classic"}
# {"memory": 13548, "messages": 0, "messages_ready": 0,
# "messages_unacknowledged": 0, "name": "my_queue2", "node": "rabbit@my-rabbit",
# "state": "running", "type": "classic"}


# mypy: disable-error-code="var-annotated"

import json

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}


def parse_rabbitmq_queues(string_table):
    parsed = {}

    for queues in string_table:
        for queue_json in queues:
            queue = json.loads(queue_json)

            queue_name = queue.get("name")
            if queue_name is not None:
                parsed.setdefault(
                    queue_name,
                    {
                        "type": queue.get("type"),
                        "state": queue.get("state"),
                        "node": queue.get("node"),
                        "messages": queue.get("messages"),
                        "messages_ready": queue.get("messages_ready"),
                        "messages_unacknowledged": queue.get("messages_unacknowledged"),
                        "memory": queue.get("memory"),
                        "messages_publish": queue.get("message_stats", {}).get("publish"),
                        "messages_publish_rate": queue.get("message_stats", {})
                        .get("publish_details", {})
                        .get("rate"),
                    },
                )

    return parsed


def check_rabbitmq_queues(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    queue_type = data.get("type")
    if queue_type is not None:
        yield 0, "Type: %s" % queue_type.title()

    queue_state = data.get("state")
    if queue_state is not None:
        state = 0
        if not queue_state:
            state = 2
        yield (
            state,
            "Is running: %s" % str(queue_state).replace("True", "yes").replace("False", "no"),
        )

    queue_node = data.get("node")
    if queue_node is not None:
        yield 0, "Running on node: %s" % queue_node

    for msg_key, infotext, param_key in [
        ("messages", "Total number of messages", "msg"),
        ("messages_ready", "Messages ready", "msg_ready"),
        ("messages_unacknowledged", "Messages unacknowledged", "msg_unack"),
        ("messages_publish", "Messages published", "msg_publish_upper"),
        ("messages_publish_rate", "Rate", "msg_publish_rate"),
    ]:
        msg_value = data.get(msg_key)
        if msg_value is None:
            continue

        unit = ""
        if "rate" in msg_key:
            unit = "1/s"

        msg_levels_upper = params.get("%s_upper" % param_key, (None, None))
        msg_levels_lower = params.get("%s_lower" % param_key, (None, None))

        yield check_levels(
            msg_value,
            msg_key,
            msg_levels_upper + msg_levels_lower,
            human_readable_func=int,
            unit=unit,
            infoname=infotext,
        )

    queue_memory = data.get("memory")
    if queue_memory is not None:
        yield check_levels(
            queue_memory,
            "mem_lnx_total_used",
            params.get("abs_memory"),
            human_readable_func=render.bytes,
            infoname="Memory used",
        )


def discover_rabbitmq_queues(section):
    yield from ((item, {}) for item in section)


check_info["rabbitmq_queues"] = LegacyCheckDefinition(
    name="rabbitmq_queues",
    parse_function=parse_rabbitmq_queues,
    service_name="RabbitMQ Queue %s",
    discovery_function=discover_rabbitmq_queues,
    check_function=check_rabbitmq_queues,
    check_ruleset_name="rabbitmq_queues",
)
