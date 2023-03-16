#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.bgp_peer as bgp_peer
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
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
    assert bgp_peer.parse_arista_bgp([data]) == result


@pytest.mark.parametrize(
    "data, result",
    [
        (
            DATA_SIMPLE,
            [
                Service(item="192.168.1.2"),
            ],
        ),
    ],
)
def test_bgp_peer_discover(data: StringByteTable, result: DiscoveryResult) -> None:
    assert list(bgp_peer.discover_arista_bgp(bgp_peer.parse_arista_bgp([data]))) == result


@pytest.mark.parametrize(
    "item, data, result",
    [
        (
            "192.168.1.2",
            DATA_SIMPLE,
            [
                Result(state=State.OK, summary="Local address: '192.168.1.1'"),
                Result(state=State.OK, summary="Local identifier: '10.10.10.10'"),
                Result(state=State.OK, summary="Remote AS number: 65000"),
                Result(state=State.OK, summary="Remote identifier: '192.168.2.0'"),
                Result(state=State.OK, summary="Admin state: 'running'"),
                Result(state=State.OK, summary="Peer state: 'established'"),
                Result(
                    state=State.OK,
                    summary="Last received error: 'Cease/other configuration change'",
                ),
                Result(state=State.OK, summary="BGP version: 4"),
                Result(state=State.OK, summary="Remote address: '192.168.1.2'"),
            ],
        ),
    ],
)
def test_bgp_peer_check(item: str, data: StringByteTable, result: CheckResult) -> None:
    assert list(bgp_peer.check_arista_bgp(item, bgp_peer.parse_arista_bgp([data]))) == result
