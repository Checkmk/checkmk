#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring statistics of MQTT brokers with Checkmk

Useful information:

https://github.com/mqtt/mqtt.org/wiki/SYS-Topics

There is also this article that you might want to have a look at:

https://www.hivemq.com/blog/why-you-shouldnt-use-sys-topics-for-monitoring

That's all well and good, but the information available really seems to fit our needs, so we use
this interface anyway.

The most important take away is: In multi-tentant, enterprise level cluster this agent may not be
useful or probably only when directly connecting to single nodes - not sure about the later.
"""

import logging
import sys
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Mapping, MutableMapping, Optional, Sequence, Set

import paho.mqtt.client as mqtt  # type: ignore[import]

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser

LOGGER = logging.getLogger("agent_mqtt")

EXPECTED_SYS_TOPICS = [
    "$SYS/broker/version",
    "$SYS/broker/uptime",
    "$SYS/broker/load/sockets/1min",
    "$SYS/broker/subscriptions/count",
    "$SYS/broker/clients/connected",
    # Seems to be not updated that often. If it's there fine, otherwise don't wait for it.
    # "$SYS/broker/clients/maximum",
    "$SYS/broker/clients/total",
    "$SYS/broker/load/connections/1min",
    "$SYS/broker/bytes/received",
    "$SYS/broker/load/bytes/received",
    "$SYS/broker/bytes/sent",
    "$SYS/broker/load/bytes/sent",
    "$SYS/broker/messages/received",
    "$SYS/broker/messages/sent",
    "$SYS/broker/publish/bytes/received",
    "$SYS/broker/publish/bytes/sent",
    "$SYS/broker/publish/messages/received",
    "$SYS/broker/messages/publish/received",
    "$SYS/broker/publish/messages/sent",
    "$SYS/broker/messages/publish/sent",
    "$SYS/broker/retained messages/count",
    "$SYS/broker/store/messages/bytes",
    "$SYS/broker/store/messages/count",
]

SYS_TOPIC_ALIASES = {
    "$SYS/broker/bytes/received": "$SYS/broker/load/bytes/received",
    "$SYS/broker/load/bytes/received": "$SYS/broker/bytes/received",
    "$SYS/broker/bytes/sent": "$SYS/broker/load/bytes/sent",
    "$SYS/broker/load/bytes/sent": "$SYS/broker/bytes/sent",
    "$SYS/broker/publish/messages/received": "$SYS/broker/messages/publish/received",
    "$SYS/broker/messages/publish/received": "$SYS/broker/publish/messages/received",
    "$SYS/broker/publish/messages/sent": "$SYS/broker/messages/publish/sent",
    "$SYS/broker/messages/publish/sent": "$SYS/broker/publish/messages/sent",
}


@dataclass
class ReceivedData:
    connected: bool = False
    subscribed_to_sys: bool = False
    topics: MutableMapping[str, str] = field(default_factory=dict)
    remaining_topics: Set[str] = field(default_factory=lambda: set(EXPECTED_SYS_TOPICS))


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "address",
        type=str,
        metavar="SERVER",
        help="Address used for connecting to the server",
    )
    parser.add_argument(
        "--port",
        type=int,
        metavar="PORT_NUM",
        help="Port used for connecting to the server",
        default=1883,
    )
    parser.add_argument(
        "--protocol",
        type=str,
        choices=["MQTTv31", "MQTTv311", "MQTTv5"],
        default="MQTTv311",
        metavar="PROTOCOL",
        help="MQTT protocol to use ('MQTTv31', 'MQTTv311' or 'MQTTv5')",
    )
    parser.add_argument(
        "--username",
        type=str,
        metavar="USER",
        help="Username for broker authentication",
    )
    parser.add_argument(
        "--password",
        type=str,
        metavar="PASSWORD",
        help="Password for broker authentication",
    )
    parser.add_argument(
        "--client-id",
        type=str,
        metavar="CLIENT_ID",
        help="Unique client ID used for the broker. Will be randomly generated when not set.",
    )
    parser.add_argument(
        "--instance-id",
        type=str,
        default="broker",
        metavar="INSTANCE_ID",
        help="Unique ID used to identify the instance on the host within Checkmk.",
    )
    return parser.parse_args(argv)


def agent_mqtt_main(args: Args) -> None:
    try:
        received = receive_from_mqtt(args)
    except RuntimeError as e:
        if args.debug:
            raise
        print(str(e), file=sys.stderr)
        sys.exit(1)

    with SectionWriter("mqtt_statistics") as writer:
        writer.append_json({args.instance_id: received.topics})
    sys.exit(0)


def receive_from_mqtt(args: Args) -> ReceivedData:
    received = ReceivedData()

    # Have a look at https://github.com/eclipse/paho.mqtt.python for an API description
    mqttc = mqtt.Client(args.client_id, userdata=received)
    mqttc.enable_logger(LOGGER)

    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_subscribe = on_subscribe

    # TODO: mqttc.tls_set

    if args.username:
        mqttc.username_pw_set(args.username, args.password)

    try:
        mqttc.connect(args.address, args.port, keepalive=60)
    except OSError as e:
        raise RuntimeError(f"Failed to connect to {args.address}:{args.port}: {e}") from e

    # We should get all our information directly on connect. Since there are brokers which do not
    # report all the topics we want for our checks or some report even more, we need some kind of
    # heuristic to stop waiting. We know the topics we expect and once we got all of them, we stop
    # waiting. Otherwise, we stop waiting after 11 seconds. We wait so long, because the
    # sys_interval of mosquitto is 10 seconds by default.
    wait_for = 11
    started_at = time.time()
    while received.remaining_topics and time.time() - started_at < wait_for:
        mqttc.loop()

    if not received.connected:
        raise RuntimeError("Not connected")

    if not received.subscribed_to_sys:
        raise RuntimeError("Not subscribed")

    LOGGER.info("Received %d topics within %d seconds", len(received.topics), wait_for)
    LOGGER.debug(received.topics)

    if not received.topics:
        raise RuntimeError("Received no topics below '$SYS/'. Please check your permmissions")

    return received


def on_connect(
    mqttc: mqtt.Client, received: ReceivedData, flags: Mapping[str, int], rc: int
) -> None:
    if rc != 0:
        raise RuntimeError(f"Failed to connect: {mqtt.error_string(rc)}")
    received.connected = True
    result, _mid = mqttc.subscribe("$SYS/#", qos=0)
    if result != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError(f"Failed to subscribe: {mqtt.error_string(result)}")


def on_subscribe(
    mqttc: mqtt.Client, received: ReceivedData, mid: int, granted_qos: Sequence[int]
) -> None:
    received.subscribed_to_sys = True


def on_message(mqttc: mqtt.Client, received: ReceivedData, msg: mqtt.MQTTMessage) -> None:
    # Once a topic was received at least once, we remove it from our "todo" list
    with suppress(KeyError):
        received.remaining_topics.remove(msg.topic)

    # Some values may be available under different topics. Also remove the known aliases from
    # the remaining topics. The checks will use the one which is available
    if msg.topic in SYS_TOPIC_ALIASES:
        with suppress(KeyError):
            received.remaining_topics.remove(SYS_TOPIC_ALIASES[msg.topic])

    received.topics[msg.topic] = msg.payload.decode()


def main() -> None:
    special_agent_main(parse_arguments, agent_mqtt_main)
