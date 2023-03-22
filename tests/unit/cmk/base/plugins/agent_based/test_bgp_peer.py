#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.bgp_peer as bgp_peer
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringByteTable,
)

DATA_SIMPLE: StringByteTable = [
    [
        [192, 168, 1, 1],
        [10, 10, 10, 10],
        "65000",
        [192, 168, 2, 0],
        "2",
        "6",
        "Cease/other configuration change",
        "100",
        "Foo",
        "1.1.4.192.168.1.2",
    ]
]
DATA_EMPTY_IP: StringByteTable = [
    [
        [],
        [0, 0, 0, 0],
        "65007",
        [0, 0, 0, 0],
        "2",
        "1",
        "",
        "100",
        "Bar",
        "1.1.4.192.168.1.2",
    ]
]

DATA_NO_DESCRIPTION: StringByteTable = [
    [
        [192, 168, 1, 1],
        [10, 10, 10, 10],
        "65000",
        [192, 168, 2, 0],
        "2",
        "6",
        "Cease/other configuration change",
        "100",
        "1.1.4.192.168.1.2",
    ]
]


@pytest.mark.parametrize(
    "data, result",
    [
        (
            DATA_SIMPLE,
            {
                "192.168.1.2": bgp_peer.BGPData(
                    admin_state="running",
                    bgp_version=4,
                    description="Foo",
                    established_time=100,
                    last_received_error="Cease/other configuration change",
                    local_address="192.168.1.1",
                    local_identifier="10.10.10.10",
                    peer_state="established",
                    remote_as_number=65000,
                    remote_identifier="192.168.2.0",
                )
            },
        ),
        (
            DATA_EMPTY_IP,
            {
                "192.168.1.2": bgp_peer.BGPData(
                    admin_state="running",
                    bgp_version=4,
                    description="Bar",
                    established_time=100,
                    last_received_error="",
                    local_address="empty()",
                    local_identifier="0.0.0.0",
                    peer_state="idle",
                    remote_as_number=65007,
                    remote_identifier="0.0.0.0",
                ),
            },
        ),
    ],
)
def test_bgp_peer_parse(data: StringByteTable, result: bgp_peer.Section) -> None:
    assert bgp_peer.parse_bgp_peer([data]) == result


@pytest.mark.parametrize(
    "data, result",
    [
        (
            DATA_SIMPLE,
            [
                Service(item="192.168.1.2", labels=[ServiceLabel("cmk/bgp/description", "Foo")]),
            ],
        ),
        (
            DATA_NO_DESCRIPTION,
            [
                Service(item="192.168.1.2", labels=[ServiceLabel("cmk/bgp/description", "n/a")]),
            ],
        ),
    ],
)
def test_bgp_peer_discover(data: StringByteTable, result: DiscoveryResult) -> None:
    assert list(bgp_peer.discover_bgp_peer(bgp_peer.parse_bgp_peer([data]))) == result


@pytest.mark.parametrize(
    "item, data, result",
    [
        (
            "192.168.1.2",
            DATA_SIMPLE,
            [
                Result(state=State.OK, summary="Description: 'Foo'"),
                Result(state=State.OK, summary="Local address: '192.168.1.1'"),
                Result(state=State.OK, summary="Admin state: 'running'"),
                Result(state=State.OK, summary="Peer state: 'established'"),
                Result(state=State.OK, summary="Established time: 1 minute 40 seconds"),
                Result(state=State.OK, notice="Local identifier: '10.10.10.10'"),
                Result(state=State.OK, notice="Remote identifier: '192.168.2.0'"),
                Result(state=State.OK, notice="Remote AS number: 65000"),
                Result(
                    state=State.OK, notice="Last received error: 'Cease/other configuration change'"
                ),
                Result(state=State.OK, notice="BGP version: 4"),
                Result(state=State.OK, notice="Remote address: '192.168.1.2'"),
                Metric("uptime", 100),
            ],
        ),
    ],
)
def test_bgp_peer_check(item: str, data: StringByteTable, result: CheckResult) -> None:
    assert (
        list(
            bgp_peer.check_bgp_peer(
                item, bgp_peer.DEFAULT_BGP_PEER_PARAMS, bgp_peer.parse_bgp_peer([data])
            )
        )
        == result
    )
