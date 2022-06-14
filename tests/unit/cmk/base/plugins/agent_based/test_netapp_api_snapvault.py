#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.netapp_api_snapvault import (
    check_netapp_api_snapvault,
    discover_netapp_api_snapvault,
    parse_netapp_api_snapvault,
)


@pytest.mark.parametrize(
    "string_table, expected_parsed",
    [
        (
            [
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system c1",
                    "destination-location d3:my_snap",
                    "policy ABCDefault",
                    "lag-time 91486",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system i1",
                    "destination-location d1:my_snap",
                    "policy Default",
                    "lag-time 82486",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system t1",
                    "destination-location d2:my_snap",
                    "policy Default",
                    "lag-time 73487",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
            ],
            {
                "my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "t1",
                    "destination-location": "d2:my_snap",
                    "policy": "Default",
                    "lag-time": "73487",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
                "d3:my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "c1",
                    "destination-location": "d3:my_snap",
                    "policy": "ABCDefault",
                    "lag-time": "91486",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
                "d1:my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "i1",
                    "destination-location": "d1:my_snap",
                    "policy": "Default",
                    "lag-time": "82486",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
                "d2:my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "t1",
                    "destination-location": "d2:my_snap",
                    "policy": "Default",
                    "lag-time": "73487",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
            },
        ),
        (
            [
                [
                    "snapvault /vol/ipb_user/",
                    "status idle state snapvaulted",
                    "lag-time 97007",
                    "source-system 172.31.12.15",
                ],
            ],
            {
                "/vol/ipb_user/": {
                    "snapvault": "/vol/ipb_user/",
                    "status": "idle state snapvaulted",
                    "lag-time": "97007",
                    "source-system": "172.31.12.15",
                },
            },
        ),
    ],
)
def test_parse_netapp_api_snapvault(string_table, expected_parsed) -> None:
    assert parse_netapp_api_snapvault(string_table) == expected_parsed


@pytest.mark.parametrize(
    "string_table, discovery_params, expected_discovery",
    [
        (
            [
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system c1",
                    "destination-location d3:my_snap",
                    "policy ABCDefault",
                    "lag-time 91486",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system i1",
                    "destination-location d1:my_snap",
                    "policy Default",
                    "lag-time 82486",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system t1",
                    "destination-location d2:my_snap",
                    "policy Default",
                    "lag-time 73487",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
            ],
            {
                "exclude_destination_vserver": True,
            },
            [
                Service(item="my_snap"),
            ],
        ),
        (
            [
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system c1",
                    "destination-location d3:my_snap",
                    "policy ABCDefault",
                    "lag-time 91486",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system i1",
                    "destination-location d1:my_snap",
                    "policy Default",
                    "lag-time 82486",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
                [
                    "snapvault my_snap",
                    "state snapmirrored",
                    "source-system t1",
                    "destination-location d2:my_snap",
                    "policy Default",
                    "lag-time 73487",
                    "destination-system a2-b0-02",
                    "status idle",
                ],
            ],
            {
                "exclude_destination_vserver": False,
            },
            [
                Service(item="d3:my_snap"),
                Service(item="d1:my_snap"),
                Service(item="d2:my_snap"),
            ],
        ),
        (
            [
                [
                    "snapvault /vol/ipb_user/",
                    "status idle state snapvaulted",
                    "lag-time 97007",
                    "source-system 172.31.12.15",
                ],
            ],
            {
                "exclude_destination_vserver": False,
            },
            [
                Service(item="/vol/ipb_user/"),
            ],
        ),
    ],
)
def test_discover_netapp_api_snapvault(string_table, discovery_params, expected_discovery) -> None:
    assert (
        list(
            discover_netapp_api_snapvault(
                discovery_params,
                parse_netapp_api_snapvault(string_table),
            )
        )
        == expected_discovery
    )


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
            "my_snap",
            {},
            {
                "my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "c1",
                    "destination-location": "d3:my_snap",
                    "policy": "ABCDefault",
                    "lag-time": "91486",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
            },
            [
                Result(state=State.OK, summary="Source-System: c1"),
                Result(state=State.OK, summary="Destination-System: a2-b0-02"),
                Result(state=State.OK, summary="Policy: ABCDefault"),
                Result(state=State.OK, summary="Status: idle"),
                Result(state=State.OK, summary="State: snapmirrored"),
                Result(state=State.OK, summary="Lag time: 1 day 1 hour"),
            ],
        ),
        (
            "my_snap",
            {
                "policy_lag_time": [
                    ("ABC", (9000, 10000)),
                    ("ABCDef", (1, 2)),
                ]
            },
            {
                "my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "c1",
                    "destination-location": "d3:my_snap",
                    "policy": "ABCDefault",
                    "lag-time": "91486",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
            },
            [
                Result(state=State.OK, summary="Source-System: c1"),
                Result(state=State.OK, summary="Destination-System: a2-b0-02"),
                Result(state=State.OK, summary="Policy: ABCDefault"),
                Result(state=State.OK, summary="Status: idle"),
                Result(state=State.OK, summary="State: snapmirrored"),
                Result(state=State.OK, summary="Lag time: 1 day 1 hour"),
            ],
        ),
        (
            "my_snap",
            {
                "policy_lag_time": [
                    ("ABC", (9000, 10000)),
                    ("ABCDefault", (1, 2)),
                ]
            },
            {
                "my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "c1",
                    "destination-location": "d3:my_snap",
                    "policy": "ABCDefault",
                    "lag-time": "91486",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
            },
            [
                Result(state=State.OK, summary="Source-System: c1"),
                Result(state=State.OK, summary="Destination-System: a2-b0-02"),
                Result(state=State.OK, summary="Policy: ABCDefault"),
                Result(state=State.OK, summary="Status: idle"),
                Result(state=State.OK, summary="State: snapmirrored"),
                Result(
                    state=State.CRIT,
                    summary="Lag time: 1 day 1 hour (warn/crit at 1 second/2 seconds)",
                ),
            ],
        ),
        (
            "my_snap",
            {
                "policy_lag_time": [
                    ("XDP", (9000, 10000)),
                    ("XDPDef", (9000, 10000)),
                ],
                "lag_time": (3, 4),
            },
            {
                "my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "c1",
                    "destination-location": "d3:my_snap",
                    "policy": "ABCDefault",
                    "lag-time": "91486",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
            },
            [
                Result(state=State.OK, summary="Source-System: c1"),
                Result(state=State.OK, summary="Destination-System: a2-b0-02"),
                Result(state=State.OK, summary="Policy: ABCDefault"),
                Result(state=State.OK, summary="Status: idle"),
                Result(state=State.OK, summary="State: snapmirrored"),
                Result(
                    state=State.CRIT,
                    summary="Lag time: 1 day 1 hour (warn/crit at 3 seconds/4 seconds)",
                ),
            ],
        ),
        (
            "my_snap",
            {
                "lag_time": (3, 4),
            },
            {
                "my_snap": {
                    "snapvault": "my_snap",
                    "state": "snapmirrored",
                    "source-system": "c1",
                    "destination-location": "d3:my_snap",
                    "policy": "ABCDefault",
                    "lag-time": "91486",
                    "destination-system": "a2-b0-02",
                    "status": "idle",
                },
            },
            [
                Result(state=State.OK, summary="Source-System: c1"),
                Result(state=State.OK, summary="Destination-System: a2-b0-02"),
                Result(state=State.OK, summary="Policy: ABCDefault"),
                Result(state=State.OK, summary="Status: idle"),
                Result(state=State.OK, summary="State: snapmirrored"),
                Result(
                    state=State.CRIT,
                    summary="Lag time: 1 day 1 hour (warn/crit at 3 seconds/4 seconds)",
                ),
            ],
        ),
        (
            "/vol/ipb_user/",
            {},
            {
                "/vol/ipb_user/": {
                    "snapvault": "/vol/ipb_user/",
                    "status": "idle state snapvaulted",
                    "lag-time": "97007",
                    "source-system": "172.31.12.15",
                },
            },
            [
                Result(state=State.OK, summary="Source-System: 172.31.12.15"),
                Result(state=State.OK, summary="Status: idle state snapvaulted"),
                Result(state=State.OK, summary="Lag time: 1 day 2 hours"),
            ],
        ),
    ],
)
def test_check_netapp_api_snapvault(item, params, parsed, expected_result) -> None:
    assert list(check_netapp_api_snapvault(item, params, parsed)) == expected_result
