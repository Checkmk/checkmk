#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.omd.agent_based.libbroker import Queue, SectionQueues
from cmk.plugins.omd.agent_based.omd_broker_queue import (
    agent_section_omd_broker_queues,
    check,
    discover_omd_broker_queues,
)

STRINGTABLE: StringTable = [
    [
        "["
        '{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.intersite.heute_remote_1","messages":1},'
        '{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.intersite.heute_remote_2","messages":2},'
        '{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.app.piggyback-hub.payload","messages":3},'
        '{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.app.piggyback-hub.config","messages":4}'
        "]"
    ],
    [
        "["
        '{"node": "rabbit-heute_remote_1@localhost", "vhost": "/", "name":"cmk.app.piggyback-hub.payload","messages":0},'
        '{"node": "rabbit-heute_remote_1@localhost", "vhost": "/", "name":"cmk.intersite.heute","messages":0},'
        '{"node": "rabbit-heute_remote_1@localhost", "vhost": "/", "name":"cmk.app.piggyback-hub.config","messages":0}'
        "]",
    ],
    [
        "["
        '{"node": "rabbit-heute_remote_1@localhost", "vhost": "customer1", "name":"cmk.intersite.heute","messages":0},'
        '{"node": "rabbit-heute_remote_1@localhost", "vhost": "customer1", "name":"cmk.app.another-app.data","messages":2}'
        "]"
    ],
    [
        "["
        '{"node": "rabbit-heute_remote_2@localhost", "vhost": "/", "name":"cmk.app.piggyback-hub.payload","messages":0},'
        '{"node": "rabbit-heute_remote_2@localhost", "vhost": "/", "name":"cmk.app.piggyback-hub.config","messages":0}'
        "]"
    ],
]


@pytest.mark.parametrize(
    ["string_table", "expected_parsed_data"],
    [
        pytest.param(
            [
                [
                    '[{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.intersite.heute_remote_1","messages":1}]'
                ],
                [
                    '[{"node": "rabbit-heute@localhost", "vhost": "customer1", "name":"cmk.app.another-app.data","messages":2}]'
                ],
            ],
            {
                "heute": [
                    Queue(
                        vhost="/",
                        name="cmk.intersite.heute_remote_1",
                        messages=1,
                    ),
                    Queue(
                        vhost="customer1",
                        name="cmk.app.another-app.data",
                        messages=2,
                    ),
                ],
            },
            id="good data",
        ),
        pytest.param(
            [['{"error":"not_authorized","reason":"Not_Authorized"}']],
            None,
            id="error from broker (e.g. mgmt plugin disabled)",
        ),
        pytest.param([], {}, id="empty list (e.g. broker not running)"),
    ],
)
def test_parse_all_queues(string_table: StringTable, expected_parsed_data: SectionQueues) -> None:
    assert agent_section_omd_broker_queues.parse_function(string_table) == expected_parsed_data


def test_discover_broker_queue() -> None:
    parsed_sections = agent_section_omd_broker_queues.parse_function(STRINGTABLE)
    assert parsed_sections is not None
    assert list(discover_omd_broker_queues(parsed_sections)) == [
        Service(item="heute piggyback-hub"),
        Service(item="heute_remote_1 piggyback-hub"),
        Service(item="heute_remote_2 piggyback-hub"),
    ]


@pytest.mark.parametrize(
    "item, expected",
    [
        (
            "heute piggyback-hub",
            [
                Result(state=State.OK, summary="Queued application messages: 7"),
                Metric("omd_application_messages", 7),
                Result(state=State.OK, summary="Messages in queue 'payload': 3"),
                Result(state=State.OK, summary="Messages in queue 'config': 4"),
            ],
        ),
        (
            "heute intersite",
            [],
        ),
        (
            "heute_remote_1 piggyback-hub",
            [
                Result(state=State.OK, summary="Queued application messages: 0"),
                Metric("omd_application_messages", 0),
                Result(state=State.OK, summary="Messages in queue 'payload': 0"),
                Result(state=State.OK, summary="Messages in queue 'config': 0"),
            ],
        ),
    ],
)
def test_check_broker_queue(item: str, expected: list[Result]) -> None:
    parsed_sections = agent_section_omd_broker_queues.parse_function(STRINGTABLE)
    assert parsed_sections is not None
    assert list(check(item, parsed_sections)) == expected


def test_no_output_for_missing_item() -> None:
    """It's best practice, and the test below relies on it"""
    parsed_sections = agent_section_omd_broker_queues.parse_function(STRINGTABLE)
    assert parsed_sections is not None
    assert not list(check("heute non-existing-app", parsed_sections))


def _parse_with_cmk_broker_queue_info() -> SectionQueues:
    parsed = agent_section_omd_broker_queues.parse_function(
        [
            [
                "["
                '{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.intersite.heute_remote_1","messages":1},'
                '{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.intersite.heute_remote_2","messages":2},'
                '{"node": "rabbit-heute@localhost", "vhost": "/", "name":"cmk.app.cmk-broker-test.some_queue","messages":3}'
                "]"
            ]
        ]
    )
    assert parsed is not None
    return parsed


def test_cmk_broker_test_not_discovered() -> None:
    """Make sure our debuggin tool isn't discovered"""
    assert "heute cmk-broker-test" not in {
        s.item for s in discover_omd_broker_queues(_parse_with_cmk_broker_queue_info())
    }


def test_cmk_broker_test_enforcable() -> None:
    """Make sure we get *some* result, if the item is enforced"""
    assert list(check("heute cmk-broker-test", _parse_with_cmk_broker_queue_info()))
