#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<rabbitmq_cluster>>>
# {'cluster_name': 'rabbit@my-rabbit', 'message_stats': {'disk_reads': 0,
# 'disk_reads_details': {'rate': 0.0}, 'disk_writes': 0, 'disk_writes_details':
# {'rate': 0.0}}, 'churn_rates': {'channel_closed': 0,
# 'channel_closed_details': {'rate': 0.0}, 'channel_created': 0,
# 'channel_created_details': {'rate': 0.0}, 'connection_closed': 0,
# 'connection_closed_details': {'rate': 0.0}, 'connection_created':
# 0, 'connection_created_details': {'rate': 0.0}, 'queue_created': 2,
# 'queue_created_details': {'rate': 0.0}, 'queue_declared': 2,
# 'queue_declared_details': {'rate': 0.0}, 'queue_deleted': 0,
# 'queue_deleted_details': {'rate': 0.0}}, 'queue_totals':
# {'messages': 0, 'messages_details': {'rate': 0.0}, 'messages_ready': 0,
# 'messages_ready_details': {'rate': 0.0},
# 'messages_unacknowledged': 0,
# 'messages_unacknowledged_details': {'rate': 0.0}},
# 'object_totals': {'channels': 0, 'connections': 0, 'consumers': 0,
# 'exchanges': 7, 'queues': 2}}


import json

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info


def parse_rabbitmq_cluster(string_table):
    parsed = {}

    for clusters in string_table:
        try:
            cluster = json.loads(clusters[0])
        except IndexError:
            continue

        cluster_name = cluster.get("cluster_name")
        if cluster_name is None:
            continue

        info = {
            "cluster_name": cluster_name,
            "rabbitmq_version": cluster.get("rabbitmq_version"),
            "erlang_version": cluster.get("erlang_version"),
        }

        msg = {
            "messages": cluster.get("queue_totals", {}).get("messages", 0),
            "messages_ready": cluster.get("queue_totals", {}).get("messages_ready", 0),
            "messages_unacknowledged": cluster.get("queue_totals", {}).get(
                "messages_unacknowledged", 0
            ),
            "messages_rate": cluster.get("queue_totals", {})
            .get("messages_details", {})
            .get("rate", 0.0),
            "messages_publish": cluster.get("message_stats", {}).get("publish", 0),
            "messages_publish_rate": cluster.get("message_stats", {})
            .get("publish_details", {})
            .get("rate", 0.0),
            "messages_deliver": cluster.get("message_stats", {}).get("deliver_get", 0),
            "messages_deliver_rate": cluster.get("message_stats", {})
            .get("deliver_get_details", {})
            .get("rate", 0.0),
        }

        object_totals = {
            "channels": cluster.get("object_totals", {}).get("channels"),
            "connections": cluster.get("object_totals", {}).get("connections"),
            "consumers": cluster.get("object_totals", {}).get("consumers"),
            "exchanges": cluster.get("object_totals", {}).get("exchanges"),
            "queues": cluster.get("object_totals", {}).get("queues"),
        }

        parsed.update(
            {
                "info": info,
                "msg": msg,
                "object_totals": object_totals,
            }
        )

    return parsed


def inventory_rabbitmq_cluster(parsed):
    info_data = parsed.get("info")
    if info_data:
        yield None, {}


def check_rabbitmq_cluster(_no_item, params, parsed):
    info_data = parsed.get("info")
    if not info_data:
        return

    for info_key in [
        ("cluster_name"),
        ("rabbitmq_version"),
        ("erlang_version"),
    ]:
        info_value = info_data.get(info_key)
        yield 0, "{}: {}".format(info_key.replace("_", " ").capitalize(), info_value)


check_info["rabbitmq_cluster"] = LegacyCheckDefinition(
    parse_function=parse_rabbitmq_cluster,
    service_name="RabbitMQ Cluster",
    discovery_function=inventory_rabbitmq_cluster,
    check_function=check_rabbitmq_cluster,
)


def inventory_rabbitmq_cluster_messages(parsed):
    msg_data = parsed.get("msg")
    if msg_data:
        yield None, {}


def check_rabbitmq_cluster_messages(_no_item, params, parsed):
    msg_data = parsed.get("msg")
    if not msg_data:
        return

    for key, infotext, hr_func in [
        ("messages", "Total number of messages", int),
        ("messages_rate", "Rate", float),
        ("messages_ready", "Messages ready", int),
        ("messages_unacknowledged", "Messages unacknowledged", int),
        ("messages_publish", "Messages published", int),
        ("messages_publish_rate", "Rate", float),
        ("messages_deliver", "Messages delivered", int),
        ("messages_deliver_rate", "Rate", float),
    ]:
        value = msg_data.get(key)
        if value is None:
            continue

        yield _handle_output(params, value, key, infotext, hr_func)


check_info["rabbitmq_cluster.messages"] = LegacyCheckDefinition(
    service_name="RabbitMQ Cluster Messages",
    sections=["rabbitmq_cluster"],
    discovery_function=inventory_rabbitmq_cluster_messages,
    check_function=check_rabbitmq_cluster_messages,
    check_ruleset_name="rabbitmq_cluster_messages",
)


def inventory_rabbitmq_cluster_stats(parsed):
    msg_data = parsed.get("msg")
    if msg_data:
        yield None, {}


def check_rabbitmq_cluster_stats(_no_item, params, parsed):
    stats_data = parsed.get("object_totals")
    if not stats_data:
        return

    for key, infotext, hr_func in [
        ("channels", "Channels", int),
        ("connections", "Connections", int),
        ("consumers", "Consumers", int),
        ("exchanges", "Exchanges", int),
        ("queues", "Queues", int),
    ]:
        value = stats_data.get(key)
        if value is None:
            continue

        yield _handle_output(params, value, key, infotext, hr_func)


def _handle_output(params, value, key, infotext, hr_func):
    unit = ""
    if "rate" in key:
        unit = "1/s"

    levels_upper = params.get("%s_upper" % key, (None, None))
    levels_lower = params.get("%s_lower" % key, (None, None))
    return check_levels(
        value,
        key,
        levels_upper + levels_lower,
        human_readable_func=hr_func,
        unit=unit,
        infoname=infotext,
    )


check_info["rabbitmq_cluster.stats"] = LegacyCheckDefinition(
    service_name="RabbitMQ Cluster Stats",
    sections=["rabbitmq_cluster"],
    discovery_function=inventory_rabbitmq_cluster_stats,
    check_function=check_rabbitmq_cluster_stats,
    check_ruleset_name="rabbitmq_cluster_stats",
)
