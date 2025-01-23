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
from cmk.plugins.omd.agent_based.libbroker import Queue, SectionQueues
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
            [['[{"name": "rabbit-heute@localhost", "mem_used":  1000000000}]']],
            {"heute": BrokerStatus(memory=1000000000)},
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
                    """[{
                            "name": "cmk.shovel.heute->heute_remote_1",
                            "node": "rabbit-heute@localhost",
                            "state": "running",
                            "vhost": "customer1"
                        },
                        {
                            "name": "cmk.shovel.heute->heute_remote_2",
                            "node": "rabbit-heute@localhost",
                            "state": "running",
                            "vhost": "customer1"
                        }
                    ]"""
                ],
                [
                    """[{
                            "name": "cmk.shovel.heute->heute_remote_1",
                            "node": "rabbit-heute_remote@localhost",
                            "state": "starting",
                            "vhost": "customer1"
                        }
                    ]"""
                ],
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
    [({"heute": BrokerStatus(memory=1000000000)}, [Service(item="heute")]), ({}, [])],
)
def test_discover_omd_broker_status(
    section_status: SectionStatus, expected: DiscoveryResult
) -> None:
    assert list(discover_omd_broker_status(section_status, None, None)) == expected


@pytest.mark.parametrize(
    "item, section_status, section_shovels, section_queues, expected",
    [
        (
            "heute",
            {"heute": BrokerStatus(memory=1000000000)},
            {
                "heute": [
                    Shovel(name="cmk.shovel.heute->heute_remote_1", state="running"),
                    Shovel(name="cmk.shovel.heute->heute_remote_2", state="running"),
                ],
            },
            {
                "heute": [
                    Queue(vhost="/", name="cmk.intersite.heute_remote_1", messages=1),
                    Queue(vhost="/", name="cmk.intersite.heute_remote_2", messages=2),
                    Queue(vhost="/", name="cmk.app.piggyback-hub.payload", messages=3),
                ]
            },
            [
                Result(state=State.OK, summary="Memory: 954 MiB"),
                Metric("mem_used", 1000000000.0),
                Result(state=State.OK, summary="Queues: 2"),
                Result(state=State.OK, summary="Messages in queue: 3"),
                Metric("messages", 3.0),
                Result(state=State.OK, summary="Shovels running: 2"),
            ],
        ),
        (
            "heute",
            {"heute": BrokerStatus(memory=1000000000)},
            {
                "heute": [Shovel(name="cmk.shovel.heute->heute_remote_1", state="starting")],
            },
            {
                "heute": [
                    Queue(vhost="/", name="cmk.app.piggyback-hub.payload", messages=3),
                ]
            },
            [
                Result(state=State.OK, summary="Memory: 954 MiB"),
                Metric("mem_used", 1000000000.0),
                Result(state=State.OK, summary="Queues: 0"),
                Result(state=State.OK, summary="Messages in queue: 0"),
                Metric("messages", 0.0),
                Result(state=State.OK, summary="Shovels running: 0"),
                Result(state=State.OK, summary="Shovels starting: 1"),
            ],
        ),
        (
            "heute_remote",
            {"heute": BrokerStatus(memory=1000000000)},
            None,
            {
                "heute": [
                    Shovel(name="cmk.shovel.heute->heute_remote_1", state="running"),
                    Shovel(name="cmk.shovel.heute->heute_remote_2", state="running"),
                ],
            },
            [],
        ),
        (
            "heute",
            {"heute": BrokerStatus(memory=1000000000)},
            None,
            {
                "heute": [
                    Queue(vhost="customer1", name="cmk.intersite.heute_remote_1", messages=3),
                    Queue(vhost="/", name="cmk.intersite.heute_remote_2", messages=2),
                    Queue(vhost="/", name="cmk.app.piggyback-hub.payload", messages=3),
                ]
            },
            [
                Result(state=State.OK, summary="Memory: 954 MiB"),
                Metric("mem_used", 1000000000.0),
                Result(state=State.OK, summary="Queues: 2"),
                Result(state=State.OK, summary="Messages in queue: 5"),
                Metric("messages", 5.0),
            ],
        ),
    ],
)
def test_check_omd_broker_status(
    item: str,
    section_status: SectionStatus,
    section_shovels: SectionShovels,
    section_queues: SectionQueues,
    expected: CheckResult,
) -> None:
    assert (
        list(check_omd_broker_status(item, section_status, section_shovels, section_queues))
        == expected
    )
