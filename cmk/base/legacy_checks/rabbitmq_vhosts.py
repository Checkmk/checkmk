#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<rabbitmq_vhosts>>>
# {"fd_total": 1098576, "sockets_total": 973629, "mem_limit": 6808874700,
# "mem_alarm": false, "disk_free_limit": 70000000, "disk_free_alarm": false,
# "proc_total": 1088576, "run_queue": 1, "name": "rabbit@my-rabbit", "type":
# "disc", "running": true, "mem_used": 108834752, "fd_used": 35,
# "sockets_used": 0, "proc_used": 429, "gc_num": 70927, "gc_bytes_reclaimed":
# 1586846120, "io_file_handle_open_attempt_count": 13, "cluster_links":
# []}
# {"fd_total": 1048576, "sockets_total": 943629, "mem_limit": 6608874700,
# "mem_alarm": false, "disk_free_limit": 50000000, "disk_free_alarm": false,
# "proc_total": 1048576, "run_queue": 1, "name": "rabbit2@my-rabbit", "type":
# "disc", "running": true, "mem_used": 101834752, "fd_used": 33,
# "sockets_used": 0, "proc_used": 426, "gc_num": 70827, "gc_bytes_reclaimed":
# 1556846120, "io_file_handle_open_attempt_count": 11, "cluster_links":
# []}


# mypy: disable-error-code="var-annotated"

import json

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


def parse_rabbitmq_vhosts(string_table):
    parsed = {}

    for vhosts in string_table:
        for vhost_json in vhosts:
            vhost = json.loads(vhost_json)

            vhost_name = vhost.get("name")
            if vhost_name is None:
                continue

            parsed.setdefault(
                vhost_name,
                {
                    "description": vhost.get("description"),
                    "messages": vhost.get("messages"),
                    "messages_ready": vhost.get("messages_ready"),
                    "messages_unacknowledged": vhost.get("messages_unacknowledged"),
                    "message_publish": vhost.get("message_stats", {}).get("publish"),
                    "message_publish_rate": vhost.get("message_stats", {})
                    .get("publish_details", {})
                    .get("rate"),
                    "message_deliver": vhost.get("message_stats", {}).get("deliver_get"),
                    "message_deliver_rate": vhost.get("message_stats", {})
                    .get("deliver_get_details", {})
                    .get("rate"),
                },
            )

    return parsed


def check_rabbitmq_vhosts(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    vhost_desc = data.get("description")
    if vhost_desc is not None:
        yield 0, "Description: %s" % vhost_desc

    for msg_key, msg_infotext, hr_func, param_key in [
        ("messages", "Total number of messages", int, "msg"),
        ("messages_ready", "Ready messages", int, "msg_ready"),
        ("messages_unacknowledged", "Unacknowledged messages", int, "msg_unack"),
        ("message_publish", "Published messages", int, "msg_publish"),
        ("message_publish_rate", "Rate", float, "msg_publish_rate"),
        ("message_deliver", "Delivered messages", int, "msg_deliver"),
        ("message_deliver_rate", "Rate", float, "msg_deliver_rate"),
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
            human_readable_func=hr_func,
            unit=unit,
            infoname=msg_infotext,
        )


def discover_rabbitmq_vhosts(section):
    yield from ((item, {}) for item in section)


check_info["rabbitmq_vhosts"] = LegacyCheckDefinition(
    name="rabbitmq_vhosts",
    parse_function=parse_rabbitmq_vhosts,
    service_name="RabbitMQ Vhost %s",
    discovery_function=discover_rabbitmq_vhosts,
    check_function=check_rabbitmq_vhosts,
    check_ruleset_name="rabbitmq_vhosts",
)
