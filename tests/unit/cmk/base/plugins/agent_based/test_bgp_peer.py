#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.base.plugins.agent_based.bgp_peer as bgp_peer
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringByteTable


def test_bgp_peer_parse_simple() -> None:
    data: StringByteTable = [
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
    assert bgp_peer.parse_arista_bgp([data]) == {
        "192.168.1.2": {
            "Admin state": "running",
            "BGP version": 4,
            "Last received error": "Cease/other configuration change",
            "Local address": "192.168.1.1",
            "Local identifier": "10.10.10.10",
            "Peer state": "established",
            "Remote AS number": 65000,
            "Remote identifier": "192.168.2.0",
        }
    }


def test_bgp_peer_parse_empty_address() -> None:
    data: StringByteTable = [
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
    assert bgp_peer.parse_arista_bgp([data]) == {
        "192.168.1.2": {
            "Admin state": "running",
            "BGP version": 4,
            "Last received error": "",
            "Local address": "empty()",
            "Local identifier": "0.0.0.0",
            "Peer state": "idle",
            "Remote AS number": 65007,
            "Remote identifier": "0.0.0.0",
        },
    }


def test_bgp_peer_check() -> None:
    data: StringByteTable = [
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
    assert list(bgp_peer.check_arista_bgp("192.168.1.2", bgp_peer.parse_arista_bgp([data]))) == [
        Result(state=State.OK, summary="Local address: '192.168.1.1'"),
        Result(state=State.OK, summary="Local identifier: '10.10.10.10'"),
        Result(state=State.OK, summary="Remote AS number: 65000"),
        Result(state=State.OK, summary="Remote identifier: '192.168.2.0'"),
        Result(state=State.OK, summary="Admin state: 'running'"),
        Result(state=State.OK, summary="Peer state: 'established'"),
        Result(state=State.OK, summary="Last received error: 'Cease/other configuration change'"),
        Result(state=State.OK, summary="BGP version: 4"),
        Result(state=State.OK, summary="Remote address: '192.168.1.2'"),
    ]
