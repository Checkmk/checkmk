#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.sophos import check_sophos, discover_sophos, parse_sophos

# synthetic data
STRING_TABLE: StringTable = [
    ["4", "2"],
    ["6", "3"],
    ["8", "0"],
    ["9", "1"],
    ["13", "4"],
    ["15", "2"],
    ["16", "2"],
]


def test_discover_sophos_skips_undiscoverable_states_and_unknown_oids() -> None:
    assert list(discover_sophos(parse_sophos(STRING_TABLE))) == [
        ("Memory Consumption", {}),
        ("RAID", {}),
        ("Temperature", {}),
        ("Power Supply Summary", {}),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "Memory Consumption",
            (0, "Status: OK (the appliance is consuming normal memory)"),
            id="state_2_is_ok",
        ),
        pytest.param(
            "RAID",
            (1, "Status: warn (the appliance RAID system is operating abnormally)"),
            id="state_3_is_warn",
        ),
        pytest.param(
            "Temperature",
            (
                2,
                "Status: error (the appliance is operating outside an acceptable temperature range)",
            ),
            id="state_4_is_crit",
        ),
        pytest.param(
            "Power Supply Left",
            (3, "Status: unknown"),
            id="state_0_is_unknown_without_detail",
        ),
        pytest.param(
            "Power Supply Right",
            (3, "Status: disabled"),
            id="state_1_is_unknown_without_detail",
        ),
    ],
)
def test_check_sophos(item: str, expected_result: tuple[int, str]) -> None:
    assert check_sophos(item, None, parse_sophos(STRING_TABLE)) == expected_result


def test_check_sophos_unknown_item() -> None:
    assert check_sophos("Fan Left", None, parse_sophos(STRING_TABLE)) is None
