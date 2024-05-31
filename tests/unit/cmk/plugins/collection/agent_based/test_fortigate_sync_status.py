#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.fortigate_sync_status import (
    check_fortigate_sync_status,
    discover_fortigate_sync_status,
    parse_fortigate_sync_status,
)

STRING_TABLE = [[["FW-VPN-RZ1", "1"], ["FW-VPN-RZ2", "0"]]]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service()],
            id="If the length of the input is more than 1, a Service with no item is discovered.",
        ),
        pytest.param(
            [
                [
                    ["FW-VPN-RZ1", "1"],
                ]
            ],
            [],
            id="If there is only one item in the input, nothing is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_vxvm_multipath(
    section: Sequence[StringTable],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_fortigate_sync_status(parse_fortigate_sync_status(section)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Result(state=State.OK, summary="FW-VPN-RZ1: synchronized"),
                Result(state=State.CRIT, summary="FW-VPN-RZ2: unsynchronized"),
            ],
            id="If one of the items has an 'unsynchronized' status, the check state is CRIT.",
        ),
        pytest.param(
            [[["FW-VPN-RZ1", "1"], ["FW-VPN-RZ2", "1"]]],
            [
                Result(state=State.OK, summary="FW-VPN-RZ1: synchronized"),
                Result(state=State.OK, summary="FW-VPN-RZ2: synchronized"),
            ],
            id="If both items have a 'synchronized' status, the check state is OK.",
        ),
        pytest.param(
            [],
            [],
            id="If the input section is empty, there are no results.",
        ),
        pytest.param(
            [[["FW-VPN-RZ1", "1"], ["FW-VPN-RZ2", "3"]]],
            [
                Result(state=State.OK, summary="FW-VPN-RZ1: synchronized"),
                Result(state=State.UNKNOWN, summary="FW-VPN-RZ2: Unknown status 3"),
            ],
            id="If the status of one item is not 1 or 0, the check state is UNKNOWN and in the description the value of the status is indicated.",
        ),
        pytest.param(
            [[["FW-VPN-RZ1", "1"], ["FW-VPN-RZ2", ""]]],
            [
                Result(state=State.OK, summary="FW-VPN-RZ1: synchronized"),
                Result(state=State.UNKNOWN, summary="FW-VPN-RZ2: Status not available"),
            ],
            id="If the status of one item is not available, the check state is UNKNOWN and in the description it's indicated that the status is not available.",
        ),
    ],
)
def test_check_fortigate_sync_status(
    section: Sequence[StringTable],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_fortigate_sync_status(
                section=parse_fortigate_sync_status(section),
            )
        )
        == expected_check_result
    )
