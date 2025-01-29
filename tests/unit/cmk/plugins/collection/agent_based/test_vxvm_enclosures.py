#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.vxvm_enclosures import (
    check_vxvm_enclosures,
    discover_vxvm_enclosures,
    parse_vxvm_enclosures,
)

STRING_TABLE = [
    ["san_vc0", "SAN_VC", "02006021c03c", "CONNECTED", "IBMSVC-ALUA", "8", "0000"],
    ["md36xxf0", "MD36xxf", "6C81F66000C458900000000054331291", "CONNECTED", "A/P", "5", "0820"],
]

STRING_TABLE_WITH_ERROR = [
    ["============"],
    ["san_vc0", "SAN_VC", "02006021c03c", "CONNECTED", "IBMSVC-ALUA", "8", "0000"],
    ["md36xxf0", "MD36xxf", "6C81F66000C458900000000054331291", "CONNECTED", "A/P", "5", "0820"],
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="san_vc0"),
                Service(item="md36xxf0"),
            ],
            id="Discovery with section that has no error.",
        ),
        pytest.param(
            STRING_TABLE_WITH_ERROR,
            [
                Service(item="san_vc0"),
                Service(item="md36xxf0"),
            ],
            id="Discovery with section that has an error. Now the check can handle 'bad' input.",
        ),
    ],
)
def test_discover_vxvm_multipath(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_vxvm_enclosures(parse_vxvm_enclosures(section))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "item, section, expected_check_result",
    [
        pytest.param(
            "san_vc0",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status is CONNECTED",
                )
            ],
            id="If the status of the enclosure is CONNECTED, the state is OK.",
        ),
        pytest.param(
            "san_vc0",
            [["san_vc0", "SAN_VC", "02006021c03c", "DISCONNECTED", "IBMSVC-ALUA", "8", "0000"]],
            [
                Result(
                    state=State.CRIT,
                    summary="Status is DISCONNECTED",
                )
            ],
            id="If the status of the enclosure is not CONNECTED, the state is CRIT and the status is indicated.",
        ),
        pytest.param(
            "not_found",
            [["san_vc0", "SAN_VC", "02006021c03c", "CONNECTED", "IBMSVC-ALUA", "8", "0000"]],
            [],
            id="The item was not found, so the state is UNKNOWN.",
        ),
    ],
)
def test_check_vxvm_enclosures(
    item: str,
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_vxvm_enclosures(
                item=item,
                section=parse_vxvm_enclosures(section),
            )
        )
        == expected_check_result
    )
