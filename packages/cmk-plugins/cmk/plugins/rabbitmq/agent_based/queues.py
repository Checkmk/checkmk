#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

# <<<rabbitmq_queues>>>
# {"memory": 14332, "message_stats": {"publish": 1, "publish_details": {"rate":
# 0.0}}, "messages": 1, "messages_ready": 1, "messages_unacknowledged": 0,
# "name": "my_queue2", "node": "rabbit@my-rabbit", "state": "running", "type":
# "classic"}
# {"memory": 13548, "messages": 0, "messages_ready": 0,
# "messages_unacknowledged": 0, "name": "my_queue2", "node": "rabbit@my-rabbit",
# "state": "running", "type": "classic"}


DEFAULT_VHOST = "/"

DEFAULT_PARAMETERS = {
    "msg_upper": ("no_levels", None),
    "msg_lower": ("no_levels", None),
    "msg_ready_upper": ("no_levels", None),
    "msg_ready_lower": ("no_levels", None),
    "msg_unack_upper": ("no_levels", None),
    "msg_unack_lower": ("no_levels", None),
    "msg_publish_upper": ("no_levels", None),
    "msg_publish_lower": ("no_levels", None),
    "msg_publish_rate_upper": ("no_levels", None),
    "msg_publish_rate_lower": ("no_levels", None),
    "abs_memory": ("no_levels", None),
}


@dataclass(frozen=True)
class QueueProperties:
    type: str | None = None
    state: str | None = None
    node: str | None = None
    vhost: str | None = None
    messages: int | None = None
    messages_ready: int | None = None
    messages_unacknowledged: int | None = None
    memory: int | None = None
    messages_publish: int | None = None
    messages_publish_rate: float | None = None


Section = Mapping[str, QueueProperties]


def parse_rabbitmq_queues(string_table: StringTable) -> Section:
    parsed: dict[str, QueueProperties] = {}

    for queues in string_table:
        for queue_json in queues:
            queue = json.loads(queue_json)

            if (queue_name := queue.get("name")) is not None:
                if (vhost := queue.get("vhost")) is not None:
                    queue_name = queue_name if vhost == DEFAULT_VHOST else f"{vhost}/{queue_name}"
                parsed.setdefault(
                    queue_name,
                    QueueProperties(
                        type=queue.get("type"),
                        state=queue.get("state"),
                        node=queue.get("node"),
                        vhost=queue.get("vhost"),
                        messages=queue.get("messages"),
                        messages_ready=queue.get("messages_ready"),
                        messages_unacknowledged=queue.get("messages_unacknowledged"),
                        memory=queue.get("memory"),
                        messages_publish=queue.get("message_stats", {}).get("publish"),
                        messages_publish_rate=queue.get("message_stats", {})
                        .get("publish_details", {})
                        .get("rate"),
                    ),
                )

    return parsed


agent_section_rabbitmq_queues = AgentSection(
    name="rabbitmq_queues",
    parse_function=parse_rabbitmq_queues,
)


def check_rabbitmq_queues(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    if data.type is not None:
        yield Result(state=State.OK, summary="Type: %s" % data.type.title())

    if data.state is not None:
        state = State.OK
        if not data.state:
            state = State.CRIT
        yield Result(
            state=state,
            summary="Is running: %s"
            % str(data.state).replace("True", "yes").replace("False", "no"),
        )

    if data.node is not None:
        yield Result(state=State.OK, summary="Running on node: %s" % data.node)

    if data.vhost is not None:
        yield Result(state=State.OK, summary="Running on vhost: %s" % data.vhost)

    for value, msg_key, infotext, param_key in [
        (data.messages, "messages", "Total number of messages", "msg"),
        (data.messages_ready, "messages_ready", "Messages ready", "msg_ready"),
        (
            data.messages_unacknowledged,
            "messages_unacknowledged",
            "Messages unacknowledged",
            "msg_unack",
        ),
        (data.messages_publish, "messages_publish", "Messages published", "msg_publish"),
    ]:
        if value is None:
            continue

        yield from check_levels(
            value,
            levels_upper=params[f"{param_key}_upper"],
            levels_lower=params[f"{param_key}_lower"],
            metric_name=msg_key,
            render_func=lambda v: str(int(v)),
            label=infotext,
        )

    if data.messages_publish_rate is not None:
        yield from check_levels(
            data.messages_publish_rate,
            levels_upper=params["msg_publish_rate_upper"],
            levels_lower=params["msg_publish_rate_lower"],
            metric_name="messages_publish_rate",
            render_func=lambda v: f"{v:.0f} 1/s",
            label="Rate",
        )

    if data.memory is not None:
        yield from check_levels(
            data.memory,
            metric_name="mem_lnx_total_used",
            levels_upper=params["abs_memory"],
            render_func=render.bytes,
            label="Memory used",
        )


def discover_rabbitmq_queues(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


check_plugin_rabbitmq_queues = CheckPlugin(
    name="rabbitmq_queues",
    service_name="RabbitMQ Queue %s",
    discovery_function=discover_rabbitmq_queues,
    check_function=check_rabbitmq_queues,
    check_ruleset_name="rabbitmq_queues",
    check_default_parameters=DEFAULT_PARAMETERS,
)
