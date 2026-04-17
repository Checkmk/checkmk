#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.ibm.agent_based.ibm_svc_array import (
    check_ibm_svc_array,
    discover_ibm_svc_array,
    parse_ibm_svc_array,
)

_STRING_TABLE: StringTable = [
    [
        "27",
        "SSD_mdisk27",
        "online",
        "1",
        "POOL_0_V7000_RZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
    [
        "28",
        "SSD_mdisk28",
        "online",
        "2",
        "POOL_1_V7000_BRZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
    [
        "29",
        "SSD_mdisk0",
        "online",
        "1",
        "POOL_0_V7000_RZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
    [
        "30",
        "SSD_mdisk1",
        "online",
        "2",
        "POOL_1_V7000_BRZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
]


def test_discover_ibm_svc_array() -> None:
    parsed = parse_ibm_svc_array(_STRING_TABLE)
    result = list(discover_ibm_svc_array(parsed))
    assert sorted(result, key=lambda s: s.item or "") == [
        Service(item="27"),
        Service(item="28"),
        Service(item="29"),
        Service(item="30"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "27",
            [
                Result(
                    state=State.OK, summary="Status: online, RAID Level: raid1, Tier: generic_ssd"
                )
            ],
        ),
        (
            "28",
            [
                Result(
                    state=State.OK, summary="Status: online, RAID Level: raid1, Tier: generic_ssd"
                )
            ],
        ),
        (
            "29",
            [
                Result(
                    state=State.OK, summary="Status: online, RAID Level: raid1, Tier: generic_ssd"
                )
            ],
        ),
        (
            "30",
            [
                Result(
                    state=State.OK, summary="Status: online, RAID Level: raid1, Tier: generic_ssd"
                )
            ],
        ),
    ],
)
def test_check_ibm_svc_array(item: str, expected_results: list[Result]) -> None:
    parsed = parse_ibm_svc_array(_STRING_TABLE)
    result = list(check_ibm_svc_array(item, parsed))
    assert result == expected_results
