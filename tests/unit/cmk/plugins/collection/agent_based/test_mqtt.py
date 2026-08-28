#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from collections.abc import Mapping, Sequence
from typing import NamedTuple
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import mqtt
from cmk.plugins.collection.agent_based.mqtt import (
    check_mqtt_broker,
    check_mqtt_clients,
    check_mqtt_messages,
    check_mqtt_uptime,
    Clients,
    discovery_mqtt_broker,
    discovery_mqtt_clients,
    discovery_mqtt_messages,
    discovery_mqtt_uptime,
    MessageCounters,
    Messages,
    parse_mqtt,
    Statistics,
)


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store = dict[str, object]()
    monkeypatch.setattr(mqtt, "get_value_store", lambda: store)


# TODO: Seems to be useful for other check tests. Do we already have something like this? We might
# be able to generalize this with some more work.
class SectionScenario(NamedTuple):
    id: str
    string_table: StringTable
    parse_result: Mapping[str, Statistics]


class DiscoveryScenario(NamedTuple):
    section: Mapping[str, Statistics]
    expected_result: Sequence[Service]


class CheckScenario(NamedTuple):
    item: str
    section: Mapping[str, Statistics]
    value_store: dict[str, object]
    expected_result: Sequence[Result | Metric]


_SCENARIOS = []

_SCENARIOS.append(
    _SCENARIO_MOSQUITTO_1612 := SectionScenario(
        id="MOSQUITTO_1612",
        string_table=[
            [
                json.dumps(
                    {
                        "broker": {
                            "$SYS/broker/bytes/received": "207711762",
                            "$SYS/broker/bytes/sent": "208760409",
                            "$SYS/broker/load/bytes/received/15min": "11434.28",
                            "$SYS/broker/load/bytes/received/1min": "10738.42",
                            "$SYS/broker/load/bytes/received/5min": "11109.04",
                            "$SYS/broker/load/bytes/sent/15min": "10085.33",
                            "$SYS/broker/load/bytes/sent/1min": "9023.62",
                            "$SYS/broker/load/bytes/sent/5min": "9492.08",
                            "$SYS/broker/load/messages/received/15min": "241.36",
                            "$SYS/broker/load/messages/received/1min": "229.43",
                            "$SYS/broker/load/messages/received/5min": "239.94",
                            "$SYS/broker/load/messages/sent/15min": "241.72",
                            "$SYS/broker/load/messages/sent/1min": "232.90",
                            "$SYS/broker/load/messages/sent/5min": "241.58",
                            "$SYS/broker/load/publish/received/15min": "93.17",
                            "$SYS/broker/load/publish/received/1min": "92.96",
                            "$SYS/broker/load/publish/received/5min": "93.79",
                            "$SYS/broker/load/publish/sent/15min": "214.47",
                            "$SYS/broker/load/publish/sent/1min": "206.71",
                            "$SYS/broker/load/publish/sent/5min": "214.18",
                            "$SYS/broker/messages/received": "4032095",
                            "$SYS/broker/messages/sent": "4191028",
                            "$SYS/broker/publish/bytes/received": "49268835",
                            "$SYS/broker/publish/bytes/sent": "58698872",
                            "$SYS/broker/publish/messages/received": "1555524",
                            "$SYS/broker/publish/messages/sent": "3819515",
                            "$SYS/broker/store/messages/bytes": "108258",
                            "$SYS/broker/uptime": "1010229 seconds",
                            "$SYS/broker/version": "mosquitto version 1.6.12",
                        }
                    }
                )
            ]
        ],
        parse_result={
            "broker": Statistics(
                version="mosquitto version 1.6.12",
                uptime=1010229,
                socket_connections_opened_rate=None,
                subscriptions=None,
                clients=Clients(
                    connected=None,
                    maximum=None,
                    total=None,
                ),
                messages=Messages(
                    counters=MessageCounters(
                        bytes_received_total=207711762,
                        bytes_sent_total=208760409,
                        messages_received_total=4032095,
                        messages_sent_total=4191028,
                        publish_messages_received_total=1555524,
                        publish_messages_sent_total=3819515,
                        publish_bytes_received_total=49268835,
                        publish_bytes_sent_total=58698872,
                    ),
                    connect_messages_received_rate=None,
                    retained_messages_count=None,
                    stored_messages_bytes=108258,
                    stored_messages_count=None,
                ),
            )
        },
    )
)

_SCENARIOS.append(
    _SCENARIO_MOSQUITTO_1609 := SectionScenario(
        id="MOSQUITTO_1609",
        string_table=[
            [
                json.dumps(
                    {
                        "broker": {
                            "$SYS/broker/bytes/received": "52067",
                            "$SYS/broker/bytes/sent": "33556",
                            "$SYS/broker/clients/active": "14",
                            "$SYS/broker/clients/connected": "14",
                            "$SYS/broker/clients/maximum": "17",
                            "$SYS/broker/clients/total": "17",
                            "$SYS/broker/connection/omd.dmz/state": "1",
                            "$SYS/broker/load/bytes/received/15min": "3040.25",
                            "$SYS/broker/load/bytes/received/1min": "10497.61",
                            "$SYS/broker/load/bytes/received/5min": "7066.39",
                            "$SYS/broker/load/bytes/sent/15min": "2005.29",
                            "$SYS/broker/load/bytes/sent/1min": "9711.67",
                            "$SYS/broker/load/bytes/sent/5min": "4890.66",
                            "$SYS/broker/load/connections/15min": "1.22",
                            "$SYS/broker/load/connections/1min": "4.24",
                            "$SYS/broker/load/connections/5min": "2.83",
                            "$SYS/broker/load/messages/received/15min": "34.31",
                            "$SYS/broker/load/messages/received/1min": "96.48",
                            "$SYS/broker/load/messages/received/5min": "77.62",
                            "$SYS/broker/load/messages/sent/15min": "39.88",
                            "$SYS/broker/load/messages/sent/1min": "146.18",
                            "$SYS/broker/load/messages/sent/5min": "92.77",
                            "$SYS/broker/load/publish/received/15min": "6.75",
                            "$SYS/broker/load/publish/received/1min": "33.57",
                            "$SYS/broker/load/publish/received/5min": "16.68",
                            "$SYS/broker/load/publish/sent/15min": "23.49",
                            "$SYS/broker/load/publish/sent/1min": "94.69",
                            "$SYS/broker/load/publish/sent/5min": "55.11",
                            "$SYS/broker/load/sockets/15min": "1.22",
                            "$SYS/broker/load/sockets/1min": "4.24",
                            "$SYS/broker/load/sockets/5min": "2.83",
                            "$SYS/broker/messages/received": "595",
                            "$SYS/broker/messages/sent": "683",
                            "$SYS/broker/messages/stored": "182",
                            "$SYS/broker/publish/bytes/received": "33325",
                            "$SYS/broker/publish/bytes/sent": "19381",
                            "$SYS/broker/publish/messages/received": "112",
                            "$SYS/broker/publish/messages/sent": "401",
                            "$SYS/broker/retained messages/count": "185",
                            "$SYS/broker/store/messages/bytes": "6069",
                            "$SYS/broker/store/messages/count": "182",
                            "$SYS/broker/subscriptions/count": "138",
                            "$SYS/broker/uptime": "165 seconds",
                            "$SYS/broker/version": "mosquitto version 1.6.9",
                        },
                    }
                )
            ]
        ],
        parse_result={
            "broker": Statistics(
                version="mosquitto version 1.6.9",
                uptime=165,
                socket_connections_opened_rate=4.24,
                subscriptions=138,
                clients=Clients(
                    connected=14,
                    maximum=17,
                    total=17,
                ),
                messages=Messages(
                    counters=MessageCounters(
                        bytes_received_total=52067,
                        bytes_sent_total=33556,
                        messages_received_total=595,
                        messages_sent_total=683,
                        publish_messages_received_total=112,
                        publish_messages_sent_total=401,
                        publish_bytes_received_total=33325,
                        publish_bytes_sent_total=19381,
                    ),
                    connect_messages_received_rate=4.24,
                    retained_messages_count=185,
                    stored_messages_bytes=6069,
                    stored_messages_count=182,
                ),
            ),
        },
    )
)

_SCENARIOS.append(
    _SCENARIO_MOSQUITTO_212_IDLE := SectionScenario(
        id="MOSQUITTO_212_IDLE",
        string_table=[
            [
                json.dumps(
                    {
                        "broker": {
                            "$SYS/broker/bytes/received": "41256",
                            "$SYS/broker/bytes/sent": "3402121",
                            "$SYS/broker/clients/active": "0",
                            "$SYS/broker/clients/connected": "0",
                            "$SYS/broker/clients/disconnected": "0",
                            "$SYS/broker/clients/expired": "0",
                            "$SYS/broker/clients/inactive": "0",
                            "$SYS/broker/clients/total": "0",
                            "$SYS/broker/connections/socket/count": "19639",
                            "$SYS/broker/heap/current": "836047",
                            "$SYS/broker/heap/maximum": "855766",
                            "$SYS/broker/load/bytes/received/15min": "48.66",
                            "$SYS/broker/load/bytes/received/1min": "56.13",
                            "$SYS/broker/load/bytes/received/5min": "53.62",
                            "$SYS/broker/load/bytes/sent/15min": "4010.84",
                            "$SYS/broker/load/bytes/sent/1min": "4625.51",
                            "$SYS/broker/load/bytes/sent/5min": "4420.51",
                            "$SYS/broker/load/connections/1min": "2.08",
                            "$SYS/broker/load/messages/received/15min": "3.60",
                            "$SYS/broker/load/messages/received/1min": "4.16",
                            "$SYS/broker/load/messages/received/5min": "3.97",
                            "$SYS/broker/load/messages/sent/15min": "102.72",
                            "$SYS/broker/load/messages/sent/1min": "118.49",
                            "$SYS/broker/load/messages/sent/5min": "113.21",
                            "$SYS/broker/load/publish/dropped/15min": "0.00",
                            "$SYS/broker/load/publish/dropped/1min": "0.00",
                            "$SYS/broker/load/publish/dropped/5min": "0.00",
                            "$SYS/broker/load/publish/received/15min": "0.00",
                            "$SYS/broker/load/publish/received/1min": "0.00",
                            "$SYS/broker/load/publish/received/5min": "0.00",
                            "$SYS/broker/load/publish/sent/15min": "99.11",
                            "$SYS/broker/load/publish/sent/1min": "114.33",
                            "$SYS/broker/load/publish/sent/5min": "109.23",
                            "$SYS/broker/load/sockets/15min": "13.80",
                            "$SYS/broker/load/sockets/1min": "14.08",
                            "$SYS/broker/load/sockets/5min": "13.99",
                            "$SYS/broker/messages/received": "3056",
                            "$SYS/broker/messages/sent": "87096",
                            "$SYS/broker/messages/stored": "55",
                            "$SYS/broker/packet/out/bytes": "0",
                            "$SYS/broker/packet/out/count": "0",
                            "$SYS/broker/publish/bytes/received": "0",
                            "$SYS/broker/publish/bytes/sent": "364457",
                            "$SYS/broker/publish/messages/dropped": "0",
                            "$SYS/broker/publish/messages/received": "0",
                            "$SYS/broker/publish/messages/sent": "84040",
                            "$SYS/broker/retained messages/count": "55",
                            "$SYS/broker/shared_subscriptions/count": "0",
                            "$SYS/broker/store/messages/bytes": "242",
                            "$SYS/broker/store/messages/count": "55",
                            "$SYS/broker/subscriptions/count": "0",
                            "$SYS/broker/uptime": "90561 seconds",
                            "$SYS/broker/version": "mosquitto version 2.1.2",
                        },
                    }
                )
            ]
        ],
        parse_result={
            "broker": Statistics(
                version="mosquitto version 2.1.2",
                uptime=90561,
                socket_connections_opened_rate=14.08,
                subscriptions=0,
                clients=Clients(
                    connected=0,
                    maximum=None,
                    total=0,
                ),
                messages=Messages(
                    counters=MessageCounters(
                        bytes_received_total=41256,
                        bytes_sent_total=3402121,
                        messages_received_total=3056,
                        messages_sent_total=87096,
                        publish_messages_received_total=0,
                        publish_messages_sent_total=84040,
                        publish_bytes_received_total=0,
                        publish_bytes_sent_total=364457,
                    ),
                    connect_messages_received_rate=2.08,
                    retained_messages_count=55,
                    stored_messages_bytes=242,
                    stored_messages_count=55,
                ),
            ),
        },
    )
)

_SCENARIOS.append(
    _SCENARIO_EMPTY := SectionScenario(
        id="EMPTY",
        string_table=[[json.dumps({"empty": {}})]],
        parse_result={
            "empty": Statistics(
                version="",
                uptime=None,
                socket_connections_opened_rate=None,
                subscriptions=None,
                clients=Clients(
                    connected=None,
                    maximum=None,
                    total=None,
                ),
                messages=Messages(
                    counters=MessageCounters(
                        bytes_received_total=None,
                        bytes_sent_total=None,
                        messages_received_total=None,
                        messages_sent_total=None,
                        publish_messages_received_total=None,
                        publish_messages_sent_total=None,
                        publish_bytes_received_total=None,
                        publish_bytes_sent_total=None,
                    ),
                    connect_messages_received_rate=None,
                    retained_messages_count=None,
                    stored_messages_bytes=None,
                    stored_messages_count=None,
                ),
            ),
        },
    ),
)


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=[s.id for s in _SCENARIOS])
def test_parse_mqtt(scenario: SectionScenario) -> None:
    assert parse_mqtt(scenario.string_table) == scenario.parse_result


@pytest.mark.parametrize(
    "discovery_scenario",
    [
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                expected_result=[],
            ),
            id="broker",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_212_IDLE.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker_2.1.2_idle",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_EMPTY.parse_result,
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_discovery_mqtt_broker(discovery_scenario: DiscoveryScenario) -> None:
    assert (
        list(discovery_mqtt_broker(discovery_scenario.section))
        == discovery_scenario.expected_result
    )


@pytest.mark.parametrize(
    "discovery_scenario",
    [
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_EMPTY.parse_result,
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_discovery_mqtt_uptime(discovery_scenario: DiscoveryScenario) -> None:
    assert (
        list(discovery_mqtt_uptime(discovery_scenario.section))
        == discovery_scenario.expected_result
    )


@pytest.mark.parametrize(
    "check_scenario",
    [
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={},
                expected_result=[
                    Result(state=State.OK, summary="Up since 1988-05-28 00:22:51"),
                    Result(state=State.OK, summary="Uptime: 11 days 16 hours"),
                    Metric("uptime", 1010229.0),
                ],
            ),
            id="broker",
        ),
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                value_store={},
                expected_result=[
                    Result(state=State.OK, summary="Up since 1988-06-08 16:57:15"),
                    Result(state=State.OK, summary="Uptime: 2 minutes 45 seconds"),
                    Metric("uptime", 165.0),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            CheckScenario(
                item="not_existing",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="not_existing",
        ),
        pytest.param(
            CheckScenario(
                item="empty",
                section=_SCENARIO_EMPTY.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_check_mqtt_uptime(check_scenario: CheckScenario, monkeypatch: pytest.MonkeyPatch) -> None:
    if check_scenario.value_store:
        monkeypatch.setattr(mqtt, "get_value_store", check_scenario.value_store.copy)
    with time_machine.travel(datetime.datetime.fromtimestamp(581792400, tz=ZoneInfo("UTC"))):
        assert (
            list(check_mqtt_uptime(check_scenario.item, check_scenario.section))
            == check_scenario.expected_result
        )


@pytest.mark.parametrize(
    "check_scenario",
    [
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="broker",
        ),
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                value_store={},
                expected_result=[
                    Result(state=State.OK, summary="Subscriptions: 138"),
                    Metric("subscriptions", 138.0),
                    Result(state=State.OK, summary="Connections Opened Received: 0.07/s"),
                    Metric("connections_opened_received_rate", 0.07066666666666667),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_212_IDLE.parse_result,
                value_store={},
                expected_result=[
                    Result(state=State.OK, summary="Subscriptions: 0"),
                    Metric("subscriptions", 0.0),
                    Result(state=State.OK, summary="Connections Opened Received: 0.23/s"),
                    Metric("connections_opened_received_rate", 0.23466666666666666),
                ],
            ),
            id="broker_2.1.2_idle",
        ),
        pytest.param(
            CheckScenario(
                item="not_existing",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="not_existing",
        ),
        pytest.param(
            CheckScenario(
                item="empty",
                section=_SCENARIO_EMPTY.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_check_mqtt_broker(check_scenario: CheckScenario, monkeypatch: pytest.MonkeyPatch) -> None:
    if check_scenario.value_store:
        monkeypatch.setattr(mqtt, "get_value_store", check_scenario.value_store.copy)
    with time_machine.travel(datetime.datetime.fromtimestamp(581792400, tz=ZoneInfo("UTC"))):
        assert (
            list(check_mqtt_broker(check_scenario.item, check_scenario.section))
            == check_scenario.expected_result
        )


@pytest.mark.parametrize(
    "discovery_scenario",
    [
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_EMPTY.parse_result,
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_discovery_mqtt_messages(discovery_scenario: DiscoveryScenario) -> None:
    assert (
        list(discovery_mqtt_messages(discovery_scenario.section))
        == discovery_scenario.expected_result
    )


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "check_scenario",
    [
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={
                    "bytes_received_total": (581792340, 207711762 - 1024 * 1024),
                    "bytes_sent_total": (581792340, 208760409 - 1024 * 1024 * 5),
                    "messages_received_total": (581792340, 4032095 - 1000),
                    "messages_sent_total": (581792340, 4191028 - 10000),
                    "publish_bytes_received_total": (581792340, 49268835 - 1024),
                    "publish_bytes_sent_total": (581792340, 58698872 - 2048),
                    "publish_messages_received_total": (581792340, 1555524 - 1337),
                    "publish_messages_sent_total": (581792340, 3819515 - 1234),
                },
                expected_result=[
                    Result(state=State.OK, summary="Stored message bytes: 106 KiB"),
                    Metric("stored_messages_bytes", 108258.0),
                    Result(state=State.OK, summary="Bytes Received: 17.1 KiB/s"),
                    Metric("bytes_received_rate", 17476.266666666666),
                    Result(state=State.OK, summary="Bytes Sent: 85.3 KiB/s"),
                    Metric("bytes_sent_rate", 87381.33333333333),
                    Result(state=State.OK, summary="Messages Received: 16.67/s"),
                    Metric("messages_received_rate", 16.666666666666668),
                    Result(state=State.OK, summary="Messages Sent: 166.67/s"),
                    Metric("messages_sent_rate", 166.66666666666666),
                    Result(state=State.OK, summary="Publish Bytes Received: 17 B/s"),
                    Metric("publish_bytes_received_rate", 17.066666666666666),
                    Result(state=State.OK, summary="Publish Bytes Sent: 34 B/s"),
                    Metric("publish_bytes_sent_rate", 34.13333333333333),
                    Result(state=State.OK, summary="Publish Messages Received: 22.28/s"),
                    Metric("publish_messages_received_rate", 22.283333333333335),
                    Result(state=State.OK, summary="Publish Messages Sent: 20.57/s"),
                    Metric("publish_messages_sent_rate", 20.566666666666666),
                ],
            ),
            id="broker",
        ),
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                value_store={
                    "bytes_received_total": (581792340, 10),
                    "bytes_sent_total": (581792340, 10),
                    "messages_received_total": (581792340, 10),
                    "messages_sent_total": (581792340, 10),
                    "publish_bytes_received_total": (581792340, 10),
                    "publish_bytes_sent_total": (581792340, 10),
                    "publish_messages_received_total": (581792340, 10),
                    "publish_messages_sent_total": (581792340, 10),
                },
                expected_result=[
                    Result(state=State.OK, summary="Retained messages: 185"),
                    Metric("retained_messages", 185.0),
                    Result(state=State.OK, summary="Stored messages: 182"),
                    Metric("stored_messages", 182.0),
                    Result(state=State.OK, summary="Stored message bytes: 5.93 KiB"),
                    Metric("stored_messages_bytes", 6069.0),
                    Result(state=State.OK, summary="Connect Messages Received: 0.07/s"),
                    Metric("connect_messages_received_rate", 0.07066666666666667),
                    Result(state=State.OK, summary="Bytes Received: 868 B/s"),
                    Metric("bytes_received_rate", 867.6166666666667),
                    Result(state=State.OK, summary="Bytes Sent: 559 B/s"),
                    Metric("bytes_sent_rate", 559.1),
                    Result(state=State.OK, summary="Messages Received: 9.75/s"),
                    Metric("messages_received_rate", 9.75),
                    Result(state=State.OK, summary="Messages Sent: 11.22/s"),
                    Metric("messages_sent_rate", 11.216666666666667),
                    Result(state=State.OK, summary="Publish Bytes Received: 555 B/s"),
                    Metric("publish_bytes_received_rate", 555.25),
                    Result(state=State.OK, summary="Publish Bytes Sent: 323 B/s"),
                    Metric("publish_bytes_sent_rate", 322.85),
                    Result(state=State.OK, summary="Publish Messages Received: 1.70/s"),
                    Metric("publish_messages_received_rate", 1.7),
                    Result(state=State.OK, summary="Publish Messages Sent: 6.52/s"),
                    Metric("publish_messages_sent_rate", 6.516666666666667),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_212_IDLE.parse_result,
                value_store={
                    "bytes_received_total": (581792340, 41256 - 600),
                    "bytes_sent_total": (581792340, 3402121 - 6000),
                    "messages_received_total": (581792340, 3056 - 60),
                    "messages_sent_total": (581792340, 87096 - 600),
                    "publish_bytes_received_total": (581792340, 0),
                    "publish_bytes_sent_total": (581792340, 364457 - 1200),
                    "publish_messages_received_total": (581792340, 0),
                    "publish_messages_sent_total": (581792340, 84040 - 120),
                },
                expected_result=[
                    Result(state=State.OK, summary="Retained messages: 55"),
                    Metric("retained_messages", 55.0),
                    Result(state=State.OK, summary="Stored messages: 55"),
                    Metric("stored_messages", 55.0),
                    Result(state=State.OK, summary="Stored message bytes: 242 B"),
                    Metric("stored_messages_bytes", 242.0),
                    Result(state=State.OK, summary="Connect Messages Received: 0.03/s"),
                    Metric("connect_messages_received_rate", 0.034666666666666665),
                    Result(state=State.OK, summary="Bytes Received: 10 B/s"),
                    Metric("bytes_received_rate", 10.0),
                    Result(state=State.OK, summary="Bytes Sent: 100 B/s"),
                    Metric("bytes_sent_rate", 100.0),
                    Result(state=State.OK, summary="Messages Received: 1.00/s"),
                    Metric("messages_received_rate", 1.0),
                    Result(state=State.OK, summary="Messages Sent: 10.00/s"),
                    Metric("messages_sent_rate", 10.0),
                    Result(state=State.OK, summary="Publish Bytes Received: 0 B/s"),
                    Metric("publish_bytes_received_rate", 0.0),
                    Result(state=State.OK, summary="Publish Bytes Sent: 20 B/s"),
                    Metric("publish_bytes_sent_rate", 20.0),
                    Result(state=State.OK, summary="Publish Messages Received: 0.00/s"),
                    Metric("publish_messages_received_rate", 0.0),
                    Result(state=State.OK, summary="Publish Messages Sent: 2.00/s"),
                    Metric("publish_messages_sent_rate", 2.0),
                ],
            ),
            id="broker_2.1.2_idle",
        ),
        pytest.param(
            CheckScenario(
                item="not_existing",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="not_existing",
        ),
        pytest.param(
            CheckScenario(
                item="empty",
                section=_SCENARIO_EMPTY.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_check_mqtt_messages(
    check_scenario: CheckScenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    if check_scenario.value_store:
        monkeypatch.setattr(mqtt, "get_value_store", check_scenario.value_store.copy)
    with time_machine.travel(datetime.datetime.fromtimestamp(581792400, tz=ZoneInfo("UTC"))):
        assert (
            list(check_mqtt_messages(check_scenario.item, check_scenario.section))
            == check_scenario.expected_result
        )


@pytest.mark.parametrize(
    "discovery_scenario",
    [
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                expected_result=[],
            ),
            id="broker",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_MOSQUITTO_212_IDLE.parse_result,
                expected_result=[
                    Service(item="broker"),
                ],
            ),
            id="broker_2.1.2_idle",
        ),
        pytest.param(
            DiscoveryScenario(
                section=_SCENARIO_EMPTY.parse_result,
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_discovery_mqtt_clients(discovery_scenario: DiscoveryScenario) -> None:
    assert (
        list(discovery_mqtt_clients(discovery_scenario.section))
        == discovery_scenario.expected_result
    )


@pytest.mark.usefixtures("empty_value_store")
@pytest.mark.parametrize(
    "check_scenario",
    [
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="broker",
        ),
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_1609.parse_result,
                value_store={},
                expected_result=[
                    Result(state=State.OK, summary="Connected clients: 14"),
                    Metric("clients_connected", 14.0),
                    Result(state=State.OK, summary="Maximum connected (since startup): 17"),
                    Metric("clients_maximum", 17.0),
                    Result(state=State.OK, summary="Total connected: 17"),
                    Metric("clients_total", 17.0),
                ],
            ),
            id="broker_1.6.9",
        ),
        pytest.param(
            CheckScenario(
                item="broker",
                section=_SCENARIO_MOSQUITTO_212_IDLE.parse_result,
                value_store={},
                expected_result=[
                    Result(state=State.OK, summary="Connected clients: 0"),
                    Metric("clients_connected", 0.0),
                    Result(state=State.OK, summary="Total connected: 0"),
                    Metric("clients_total", 0.0),
                ],
            ),
            id="broker_2.1.2_idle",
        ),
        pytest.param(
            CheckScenario(
                item="not_existing",
                section=_SCENARIO_MOSQUITTO_1612.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="not_existing",
        ),
        pytest.param(
            CheckScenario(
                item="empty",
                section=_SCENARIO_EMPTY.parse_result,
                value_store={},
                expected_result=[],
            ),
            id="empty",
        ),
    ],
)
def test_check_mqtt_clients(check_scenario: CheckScenario, monkeypatch: pytest.MonkeyPatch) -> None:
    if check_scenario.value_store:
        monkeypatch.setattr(mqtt, "get_value_store", check_scenario.value_store.copy)
    with time_machine.travel(datetime.datetime.fromtimestamp(581792400, tz=ZoneInfo("UTC"))):
        assert (
            list(check_mqtt_clients(check_scenario.item, check_scenario.section))
            == check_scenario.expected_result
        )
