#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.omd.agent_based.omd_broker_status import (
    BrokerStatus,
    check_omd_broker_status,
    discover_omd_broker_status,
    parse_omd_broker_shovels,
    parse_omd_broker_status,
    SectionShovels,
    SectionStatus,
    Shovel,
)


@pytest.mark.parametrize(
    "string_table, expected_parsed_data",
    [
        (
            [
                [
                    """heute {
                        "memory": {
                            "atom": 100,
                            "total": {
                                "erlang": 100,
                                "rss": 1000000000,
                                "allocated": 100
                            }
                        },
                        "totals": {
                            "virtual_host_count": 2,
                            "connection_count": 3,
                            "queue_count": 4
                        }
                    }
                    """
                ],
                ["stable"],
            ],
            {"heute": BrokerStatus(memory=1000000000, queues=4)},
        ),
        ([], {}),
    ],
)
def test_parse_omd_broker_status(
    string_table: StringTable, expected_parsed_data: SectionStatus
) -> None:
    assert parse_omd_broker_status(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "string_table, expected_parsed_data",
    [
        (
            [
                [
                    """heute [{
                            "name": "cmk.shovel.heute->heute_remote_1",
                            "type": "dynamic",
                            "state": "running",
                            "source": "amqp:///customer1",
                            "vhost": "customer1",
                            "destination": "amqps://localhost:5673",
                            "termination_reason": "",
                            "destination_protocol": "amqp091",
                            "source_protocol": "amqp091",
                            "last_changed": "2024-10-10 13:15:31",
                            "source_queue": "cmk.intersite.heute_remote_1",
                            "destination_exchange": "cmk.intersite"
                        },
                        {
                            "name": "cmk.shovel.heute->heute_remote_2",
                            "type": "dynamic",
                            "state": "running",
                            "source": "amqp:///customer1",
                            "vhost": "customer1",
                            "destination": "amqps://localhost:5674",
                            "termination_reason": "",
                            "destination_protocol": "amqp091",
                            "source_protocol": "amqp091",
                            "last_changed": "2024-10-10 13:59:07",
                            "source_queue": "cmk.intersite.heute_remote_2",
                            "destination_exchange": "cmk.intersite"
                        }
                    ]"""
                ],
                [
                    """heute_remote [{
                            "name": "cmk.shovel.heute->heute_remote_1",
                            "type": "dynamic",
                            "state": "starting",
                            "source": "amqp:///customer1",
                            "vhost": "customer1",
                            "destination": "amqps://localhost:5673",
                            "termination_reason": "",
                            "destination_protocol": "amqp091",
                            "source_protocol": "amqp091",
                            "last_changed": "2024-10-10 13:15:31",
                            "source_queue": "cmk.intersite.heute_remote_1",
                            "destination_exchange": "cmk.intersite"
                        }
                    ]"""
                ],
                ["stable"],
            ],
            {
                "heute": [
                    Shovel(name="cmk.shovel.heute->heute_remote_1", state="running"),
                    Shovel(name="cmk.shovel.heute->heute_remote_2", state="running"),
                ],
                "heute_remote": [Shovel(name="cmk.shovel.heute->heute_remote_1", state="starting")],
            },
        ),
        ([], {}),
    ],
)
def test_parse_omd_broker_shovels(
    string_table: StringTable, expected_parsed_data: SectionShovels
) -> None:
    assert parse_omd_broker_shovels(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "section_status, expected",
    [({"heute": BrokerStatus(memory=1000000000, queues=4)}, [Service(item="heute")]), ({}, [])],
)
def test_discover_omd_broker_status(
    section_status: SectionStatus, expected: DiscoveryResult
) -> None:
    assert list(discover_omd_broker_status(section_status, None)) == expected


@pytest.mark.parametrize(
    "item, section_status, section_shovels, expected",
    [
        (
            "heute",
            {"heute": BrokerStatus(memory=1000000000, queues=4)},
            {
                "heute": [
                    Shovel(name="cmk.shovel.heute->heute_remote_1", state="running"),
                    Shovel(name="cmk.shovel.heute->heute_remote_2", state="running"),
                ],
            },
            [
                Result(state=State.OK, summary="Memory: 954 MiB"),
                Metric("mem_used", 1000000000.0),
                Result(state=State.OK, summary="Queues: 4"),
                Result(state=State.OK, summary="Shovels running: 2"),
            ],
        ),
        (
            "heute",
            {"heute": BrokerStatus(memory=1000000000, queues=4)},
            {
                "heute": [Shovel(name="cmk.shovel.heute->heute_remote_1", state="starting")],
            },
            [
                Result(state=State.OK, summary="Memory: 954 MiB"),
                Metric("mem_used", 1000000000.0),
                Result(state=State.OK, summary="Queues: 4"),
                Result(state=State.OK, summary="Shovels running: 0"),
                Result(state=State.OK, summary="Shovels starting: 1"),
            ],
        ),
        (
            "heute_remote",
            {"heute": BrokerStatus(memory=1000000000, queues=4)},
            {
                "heute": [
                    Shovel(name="cmk.shovel.heute->heute_remote_1", state="running"),
                    Shovel(name="cmk.shovel.heute->heute_remote_2", state="running"),
                ],
            },
            [],
        ),
    ],
)
def test_check_omd_broker_status(
    item: str,
    section_status: SectionStatus,
    section_shovels: SectionShovels,
    expected: CheckResult,
) -> None:
    assert list(check_omd_broker_status(item, section_status, section_shovels)) == expected
