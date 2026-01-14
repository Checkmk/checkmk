#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

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


import enum
import json

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition

check_info = {}


class MessageType(enum.StrEnum):
    """Watch out! The values must match the ruleset!

    For now copy'n'paste. Should go to cmk/plugins/rabbitmq sometay (TM).
    """

    TOTAL = "messages"
    TOTAL_RATE = "messages_rate"
    READY = "messages_ready"
    UNACKNOWLEDGED = "messages_unacknowledged"
    PUBLISH = "messages_publish"
    PUBLISH_RATE = "messages_publish_rate"
    DELIVER = "messages_deliver"
    DELIVER_RATE = "messages_deliver_rate"


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
            MessageType.TOTAL: cluster.get("queue_totals", {}).get("messages", 0),
            MessageType.READY: cluster.get("queue_totals", {}).get("messages_ready", 0),
            MessageType.UNACKNOWLEDGED: cluster.get("queue_totals", {}).get(
                "messages_unacknowledged", 0
            ),
            MessageType.TOTAL_RATE: cluster.get("queue_totals", {})
            .get("messages_details", {})
            .get("rate", 0.0),
            MessageType.PUBLISH: cluster.get("message_stats", {}).get("publish", 0),
            MessageType.PUBLISH_RATE: cluster.get("message_stats", {})
            .get("publish_details", {})
            .get("rate", 0.0),
            MessageType.DELIVER: cluster.get("message_stats", {}).get("deliver_get", 0),
            MessageType.DELIVER_RATE: cluster.get("message_stats", {})
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


def discover_rabbitmq_cluster(parsed):
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
    name="rabbitmq_cluster",
    parse_function=parse_rabbitmq_cluster,
    service_name="RabbitMQ Cluster",
    discovery_function=discover_rabbitmq_cluster,
    check_function=check_rabbitmq_cluster,
)


def discover_rabbitmq_cluster_messages(parsed):
    msg_data = parsed.get("msg")
    if msg_data:
        yield None, {}


def check_rabbitmq_cluster_messages(_no_item, params, parsed):
    msg_data = parsed.get("msg")
    if not msg_data:
        return

    for key, infotext, type_ in [
        (MessageType.TOTAL, "Total number of messages", int),
        (MessageType.TOTAL_RATE, "Rate", float),
        (MessageType.READY, "Messages ready", int),
        (MessageType.UNACKNOWLEDGED, "Messages unacknowledged", int),
        (MessageType.PUBLISH, "Messages published", int),
        (MessageType.PUBLISH_RATE, "Rate", float),
        (MessageType.DELIVER, "Messages delivered", int),
        (MessageType.DELIVER_RATE, "Rate", float),
    ]:
        value = msg_data.get(key)
        if value is None:
            continue

        yield _handle_output(params, type_(value), key, infotext)


check_info["rabbitmq_cluster.messages"] = LegacyCheckDefinition(
    name="rabbitmq_cluster_messages",
    service_name="RabbitMQ Cluster Messages",
    sections=["rabbitmq_cluster"],
    discovery_function=discover_rabbitmq_cluster_messages,
    check_function=check_rabbitmq_cluster_messages,
    check_ruleset_name="rabbitmq_cluster_messages",
)


def discover_rabbitmq_cluster_stats(parsed):
    msg_data = parsed.get("msg")
    if msg_data:
        yield None, {}


def check_rabbitmq_cluster_stats(_no_item, params, parsed):
    stats_data = parsed.get("object_totals")
    if not stats_data:
        return

    for key, infotext in [
        ("channels", "Channels"),
        ("connections", "Connections"),
        ("consumers", "Consumers"),
        ("exchanges", "Exchanges"),
        ("queues", "Queues"),
    ]:
        value = stats_data.get(key)
        if value is None:
            continue

        yield _handle_output(params, int(value), key, infotext)


def _handle_output(params, value, key, infotext):
    unit = "/s" if "rate" in key else ""

    levels_upper = params.get("%s_upper" % key, (None, None))
    levels_lower = params.get("%s_lower" % key, (None, None))
    return check_levels(
        value,
        key,
        levels_upper + levels_lower,
        human_readable_func=lambda x: f"{x}{unit}",
        infoname=infotext,
    )


check_info["rabbitmq_cluster.stats"] = LegacyCheckDefinition(
    name="rabbitmq_cluster_stats",
    service_name="RabbitMQ Cluster Stats",
    sections=["rabbitmq_cluster"],
    discovery_function=discover_rabbitmq_cluster_stats,
    check_function=check_rabbitmq_cluster_stats,
    check_ruleset_name="rabbitmq_cluster_stats",
)
