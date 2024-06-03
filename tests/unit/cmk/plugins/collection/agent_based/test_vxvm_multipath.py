#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.vxvm_multipath import (
    check_vxvm_multipath,
    discover_vxvm_multipath,
    parse_vxvm_multipath,
)

STRING_TABLE = [
    ["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["san_vc0_0001dc", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["md36xxf0_4", "ENABLED", "MD36xxf", "4", "4", "0", "md36xxf0"],
]

STRING_TABLE_WITH_ERROR = [
    ["===================================="],
    ["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["san_vc0_0001dc", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["md36xxf0_4", "ENABLED", "MD36xxf", "4", "4", "0", "md36xxf0"],
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="san_vc0_0001da"),
                Service(item="san_vc0_0001dc"),
                Service(item="md36xxf0_4"),
            ],
            id="Discovery with section that has no error.",
        ),
        pytest.param(
            STRING_TABLE_WITH_ERROR,
            [
                Service(item="san_vc0_0001da"),
                Service(item="san_vc0_0001dc"),
                Service(item="md36xxf0_4"),
            ],
            id="Discovery with section that has an error. Now this does not make a difference, since the parse function ignores the 'bad' input.",
        ),
    ],
)
def test_discover_vxvm_multipath(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discover_vxvm_multipath(parse_vxvm_multipath(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "item, section, expected_check_result",
    [
        pytest.param(
            "san_vc0_0001da",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: ENABLED, (8/8) Paths to enclosure san_vc0 enabled",
                )
            ],
            id="The number of active paths is the same as the number of maximum available paths. Because of that, the state is OK.",
        ),
        pytest.param(
            "san_vc0_0001da",
            [["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "5", "0", "san_vc0"]],
            [
                Result(
                    state=State.WARN,
                    summary="Status: ENABLED, (5/8) Paths to enclosure san_vc0 enabled",
                )
            ],
            id="The number of active paths is not the same as the number of maximum available paths, so the state is WARN.",
        ),
        pytest.param(
            "san_vc0_0001da",
            [["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "5", "3", "san_vc0"]],
            [
                Result(
                    state=State.WARN,
                    summary="Status: ENABLED, (5/8) Paths to enclosure san_vc0 enabled",
                )
            ],
            id="The number of inactive paths is greater than 0, so the state is CRIT.",
        ),
        pytest.param(
            "not_found",
            [["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "5", "3", "san_vc0"]],
            [],
            id="The item was not found, so the state is UNKNOWN.",
        ),
    ],
)
def test_check_vxvm_multipath(
    item: str,
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_vxvm_multipath(
                item=item,
                section=parse_vxvm_multipath(section),
            )
        )
        == expected_check_result
    )
