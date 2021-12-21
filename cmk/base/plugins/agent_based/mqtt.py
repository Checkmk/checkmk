#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Callable, Mapping, NamedTuple, Sequence

from .agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    register,
    render,
    Service,
    type_defs,
)
from .agent_based_api.v1.type_defs import CheckResult
from .utils import uptime


class Clients(NamedTuple):
    # $SYS/broker/clients/connected
    # The number of currently connected clients.
    connected: int
    # $SYS/broker/clients/maximum
    # The maximum number of clients that have been connected to the broker at the same time.
    maximum: int
    # $SYS/broker/clients/total
    # The total number of active and inactive clients currently connected and registered on the
    # broker.
    total: int


class MessageCounters(NamedTuple):
    # $SYS/broker/bytes/received
    # The total number of bytes received since the broker started.
    bytes_received_total: int
    # $SYS/broker/bytes/sent
    # The total number of bytes sent since the broker started.
    bytes_sent_total: int
    # $SYS/broker/messages/received
    # The total number of messages of any type received since the broker started.
    messages_received_total: int
    # $SYS/broker/messages/sent
    # The total number of messages of any type sent since the broker started.
    messages_sent_total: int
    # $SYS/broker/messages/publish/received
    # The total number of PUBLISH messages received since the broker started.
    publish_messages_received_total: int
    # $SYS/broker/messages/publish/sent
    # The total number of PUBLISH messages sent since the broker started.
    publish_messages_sent_total: int
    # $SYS/broker/bytes/received
    # The total number of bytes related to PUBLISH messages received since the broker started.
    publish_bytes_received_total: int
    # $SYS/broker/bytes/sent
    # The total number of bytes sent related to PUBLISH messages since the broker started.
    publish_bytes_sent_total: int


class Messages(NamedTuple):
    counters: MessageCounters

    # $SYS/broker/load/connections/1min
    # The 1 minute moving average of the number of CONNECT packets received by the broker.
    connect_messages_received_rate: float

    # $SYS/broker/retained messages/count
    # The total number of retained messages active on the broker.
    retained_messages_count: int
    # $SYS/broker/store/messages/bytes
    # The number of bytes currently held by message payloads in the message store. This includes
    # retained messages and messages queued for durable clients.
    stored_messages_bytes: int
    # $SYS/broker/store/messages/count
    # The number of messages currently held in the message store. This includes retained messages
    # and messages queued for durable clients
    stored_messages_count: int


class Statistics(NamedTuple):
    """
    https://github.com/mqtt/mqtt.org/wiki/SYS-Topics
    https://mosquitto.org/man/mosquitto-8.html
    """

    # $SYS/broker/version
    version: str
    # $SYS/broker/uptime
    uptime: int

    # $SYS/broker/load/sockets/1min
    # The 1 minute moving average of the number of socket connections opened to the broker over
    # different time intervals.
    socket_connections_opened_rate: float
    # $SYS/broker/subscriptions/count
    # The total number of subscriptions active on the broker.
    subscriptions: int

    clients: Clients
    messages: Messages


def parse_mqtt(string_table: type_defs.StringTable) -> Mapping[str, Statistics]:
    def parse_uptime(value: str) -> int:
        """
        >>> parse_uptime("11 days 16 hours 10 minutes 11 seconds")
        0
        """
        if not value:
            return 0

        try:
            scales = {
                "days": 86400,
                "hours": 3600,
                "minutes": 60,
                "seconds": 1,
            }
            parts = iter(value.strip().split(" "))
            return sum(int(num) * scales[scale] for num, scale in zip(parts, parts))
        except Exception:
            raise ValueError(f"Unhandled uptime: {value}")

    def get_first(raw: Mapping[str, str], search_topics: Sequence[str]) -> str:
        """Get the first requested topic that the broker provides

        Depending on broker and version some values may be available or not or under different
        paths.
        """
        return next((raw[t] for t in search_topics if t in raw), "")

    def parse_int(raw: Mapping[str, str], search_topics: Sequence[str]) -> int:
        try:
            return int(get_first(raw, search_topics))
        except ValueError:
            return 0

    def parse_float(raw: Mapping[str, str], search_topics: Sequence[str]) -> float:
        try:
            return float(get_first(raw, search_topics))
        except ValueError:
            return 0.0

    return {
        str(instance_id): Statistics(
            version=raw.get("$SYS/broker/version", ""),
            uptime=parse_uptime(raw.get("$SYS/broker/uptime", "")),
            socket_connections_opened_rate=parse_float(raw, ["$SYS/broker/load/sockets/1min"]),
            subscriptions=parse_int(raw, ["$SYS/broker/subscriptions/count"]),
            clients=Clients(
                connected=parse_int(raw, ["$SYS/broker/clients/connected"]),
                maximum=parse_int(raw, ["$SYS/broker/clients/maximum"]),
                total=parse_int(raw, ["$SYS/broker/clients/total"]),
            ),
            messages=Messages(
                connect_messages_received_rate=parse_float(
                    raw, ["$SYS/broker/load/connections/1min"]
                ),
                counters=MessageCounters(
                    bytes_received_total=parse_int(
                        raw, ["$SYS/broker/bytes/received", "$SYS/broker/load/bytes/received"]
                    ),
                    bytes_sent_total=parse_int(
                        raw, ["$SYS/broker/bytes/sent", "$SYS/broker/load/bytes/sent"]
                    ),
                    messages_received_total=parse_int(raw, ["$SYS/broker/messages/received"]),
                    messages_sent_total=parse_int(raw, ["$SYS/broker/messages/sent"]),
                    publish_bytes_received_total=parse_int(
                        raw, ["$SYS/broker/publish/bytes/received"]
                    ),
                    publish_bytes_sent_total=parse_int(raw, ["$SYS/broker/publish/bytes/sent"]),
                    publish_messages_received_total=parse_int(
                        raw,
                        [
                            "$SYS/broker/publish/messages/received",
                            "$SYS/broker/messages/publish/received",
                        ],
                    ),
                    publish_messages_sent_total=parse_int(
                        raw,
                        ["$SYS/broker/publish/messages/sent", "$SYS/broker/messages/publish/sent"],
                    ),
                ),
                retained_messages_count=parse_int(raw, ["$SYS/broker/retained messages/count"]),
                stored_messages_bytes=parse_int(raw, ["$SYS/broker/store/messages/bytes"]),
                stored_messages_count=parse_int(raw, ["$SYS/broker/store/messages/count"]),
            ),
        )
        for line in string_table
        for instance_id, raw in json.loads(line[0]).items()
    }


register.agent_section(
    name="mqtt_statistics",
    parse_function=parse_mqtt,
)


def discovery_mqtt_broker(section: Mapping[str, Statistics]) -> type_defs.DiscoveryResult:
    """Discover instances which report at least one of the supported values"""
    yield from (
        Service(item=instance_id)
        for instance_id, stats in section.items()
        if (stats.socket_connections_opened_rate or stats.subscriptions)
    )


def check_mqtt_broker(item: str, section: Mapping[str, Statistics]) -> CheckResult:
    stats = section.get(item)
    if stats is None:
        return

    if stats.subscriptions:
        yield from check_levels(
            stats.subscriptions, metric_name="subscriptions", label="Subscriptions", render_func=str
        )

    if connections_opened_rate := stats.socket_connections_opened_rate:
        connections_opened_per_sec = connections_opened_rate / 60
        yield from check_message_rate(
            "connections_opened_received_rate", connections_opened_per_sec
        )


register.check_plugin(
    name="mqtt_broker",
    sections=["mqtt_statistics"],
    service_name="MQTT %s Broker",
    discovery_function=discovery_mqtt_broker,
    check_function=check_mqtt_broker,
)


def discovery_mqtt_uptime(section: Mapping[str, Statistics]) -> type_defs.DiscoveryResult:
    yield from (Service(item=instance_id) for instance_id, stats in section.items() if stats.uptime)


def check_mqtt_uptime(item: str, section: Mapping[str, Statistics]) -> CheckResult:
    stats = section.get(item)
    if stats is None:
        return

    if stats.uptime:
        yield from uptime.check(params={}, section=uptime.Section(float(stats.uptime), None))


register.check_plugin(
    name="mqtt_uptime",
    sections=["mqtt_statistics"],
    service_name="MQTT %s Uptime",
    discovery_function=discovery_mqtt_uptime,
    check_function=check_mqtt_uptime,
)


def discovery_mqtt_messages(section: Mapping[str, Statistics]) -> type_defs.DiscoveryResult:
    """Discover instances which report at least one of the supported values. We only look at the
    "received". Assuming the "sent" are also there or not there."""
    yield from (
        Service(item=instance_id)
        for instance_id, stats in section.items()
        if (
            any(stats.messages.counters)
            or stats.messages.connect_messages_received_rate
            or stats.messages.retained_messages_count
            or stats.messages.stored_messages_bytes
            or stats.messages.stored_messages_bytes
        )
    )


def check_mqtt_messages(item: str, section: Mapping[str, Statistics]) -> CheckResult:
    stats = section.get(item)
    if stats is None:
        return
    messages = stats.messages

    if messages.retained_messages_count:
        yield from check_levels(
            messages.retained_messages_count,
            metric_name="retained_messages",
            label="Retained messages",
            render_func=str,
        )

    if messages.stored_messages_count:
        yield from check_levels(
            messages.stored_messages_count,
            metric_name="stored_messages",
            label="Stored messages",
            render_func=str,
        )

    if messages.stored_messages_bytes:
        yield from check_levels(
            messages.stored_messages_bytes,
            metric_name="stored_messages_bytes",
            label="Stored message bytes",
            render_func=render.bytes,
        )

    if connect_messages_rate := messages.connect_messages_received_rate:
        connect_messages_per_sec = connect_messages_rate / 60
        yield from check_message_rate("connect_messages_received_rate", connect_messages_per_sec)

    value_store = get_value_store()
    now = time.time()

    for k, v in sorted(messages.counters._asdict().items()):
        if not v:
            continue

        try:
            rate = get_rate(value_store, k, now, v)
            yield from check_message_rate(k.replace("_total", "_rate"), rate)
        except GetRateError as e:
            # Continue with other values to initialize all counters at once
            yield IgnoreResults(str(e))


def check_message_rate(k: str, rate: float) -> CheckResult:
    yield from check_levels(
        rate, metric_name=k, label=format_title(k), render_func=get_render_func(k)
    )


def format_title(k: str) -> str:
    return k.replace("_rate", "").replace("_", " ").title()


def get_render_func(k: str) -> Callable[[float], str]:
    if "bytes" in k:
        return lambda v: render.bytes(v) + "/s"
    return lambda v: f"{v:.2f}/s"


register.check_plugin(
    name="mqtt_messages",
    sections=["mqtt_statistics"],
    service_name="MQTT %s Messages",
    discovery_function=discovery_mqtt_messages,
    check_function=check_mqtt_messages,
)


def discovery_mqtt_clients(section: Mapping[str, Statistics]) -> type_defs.DiscoveryResult:
    """Discover instances which report at least one of the supported values"""
    yield from (
        Service(item=instance_id) for instance_id, stats in section.items() if any(stats.clients)
    )


def check_mqtt_clients(item: str, section: Mapping[str, Statistics]) -> CheckResult:
    stats = section.get(item)
    if stats is None:
        return
    clients = stats.clients

    if clients.connected:
        yield from check_levels(
            clients.connected,
            metric_name="clients_connected",
            label="Connected clients",
            render_func=str,
        )

    if clients.maximum:
        yield from check_levels(
            clients.maximum,
            metric_name="clients_maximum",
            label="Maximum connected (since startup)",
            render_func=str,
        )

    if clients.total:
        yield from check_levels(
            clients.total, metric_name="clients_total", label="Total connected", render_func=str
        )


register.check_plugin(
    name="mqtt_clients",
    sections=["mqtt_statistics"],
    service_name="MQTT %s Clients",
    discovery_function=discovery_mqtt_clients,
    check_function=check_mqtt_clients,
)
