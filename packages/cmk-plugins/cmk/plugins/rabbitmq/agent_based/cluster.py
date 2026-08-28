#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]


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


def parse_rabbitmq_cluster(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}

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


agent_section_rabbitmq_cluster = AgentSection(
    name="rabbitmq_cluster",
    parse_function=parse_rabbitmq_cluster,
)


def discover_rabbitmq_cluster(section: Section) -> DiscoveryResult:
    if section.get("info"):
        yield Service()


def check_rabbitmq_cluster(section: Section) -> CheckResult:
    info_data = section.get("info")
    if not info_data:
        return

    for info_key in (
        "cluster_name",
        "rabbitmq_version",
        "erlang_version",
    ):
        info_value = info_data.get(info_key)
        yield Result(
            state=State.OK,
            summary=f"{info_key.replace('_', ' ').capitalize()}: {info_value}",
        )


check_plugin_rabbitmq_cluster = CheckPlugin(
    name="rabbitmq_cluster",
    service_name="RabbitMQ Cluster",
    discovery_function=discover_rabbitmq_cluster,
    check_function=check_rabbitmq_cluster,
)


def discover_rabbitmq_cluster_messages(section: Section) -> DiscoveryResult:
    if section.get("msg"):
        yield Service()


def check_rabbitmq_cluster_messages(params: Mapping[str, Any], section: Section) -> CheckResult:
    msg_data = section.get("msg")
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

        yield from _handle_output(params, type_(value), key, infotext)


check_plugin_rabbitmq_cluster_messages = CheckPlugin(
    name="rabbitmq_cluster_messages",
    service_name="RabbitMQ Cluster Messages",
    sections=["rabbitmq_cluster"],
    discovery_function=discover_rabbitmq_cluster_messages,
    check_function=check_rabbitmq_cluster_messages,
    check_ruleset_name="rabbitmq_cluster_messages",
    check_default_parameters={},
)


def discover_rabbitmq_cluster_stats(section: Section) -> DiscoveryResult:
    if section.get("msg"):
        yield Service()


def check_rabbitmq_cluster_stats(params: Mapping[str, Any], section: Section) -> CheckResult:
    stats_data = section.get("object_totals")
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

        yield from _handle_output(params, int(value), key, infotext)


def _handle_output(params: Mapping[str, Any], value: float, key: str, infotext: str) -> CheckResult:
    unit = "/s" if "rate" in key else ""

    levels_upper = params.get(f"{key}_upper", (None, None))
    levels_lower = params.get(f"{key}_lower", (None, None))
    yield from check_levels(
        value,
        key,
        levels_upper + levels_lower,
        human_readable_func=lambda x: f"{x}{unit}",
        infoname=infotext,
    )


check_plugin_rabbitmq_cluster_stats = CheckPlugin(
    name="rabbitmq_cluster_stats",
    service_name="RabbitMQ Cluster Stats",
    sections=["rabbitmq_cluster"],
    discovery_function=discover_rabbitmq_cluster_stats,
    check_function=check_rabbitmq_cluster_stats,
    check_ruleset_name="rabbitmq_cluster_stats",
    check_default_parameters={},
)
