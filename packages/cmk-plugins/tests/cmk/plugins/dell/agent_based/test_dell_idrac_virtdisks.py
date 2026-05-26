#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.dell.agent_based.dell_idrac_virtdisks import (
    check_dell_idrac_virtdisks,
    discover_dell_idrac_virtdisks,
    parse_dell_idrac_virtdisks,
)

# Row layout: (virtualDiskName, virtualDiskState, virtualDiskLayout/raidLevel,
#              virtualDiskComponentStatus, virtualDiskRemainingRedundancy)
_STRING_TABLE: StringTable = [
    ["System", "2", "4", "3", "1"],
    ["Backup", "3", "5", "5", "0"],
    ["", "2", "4", "3", "1"],
]


def test_parse_dell_idrac_virtdisks() -> None:
    assert parse_dell_idrac_virtdisks(_STRING_TABLE) == _STRING_TABLE


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            {"System", "Backup"},
        ),
        (
            [["System", "2", "4", "3", "1"]],
            {
                "System",
            },
        ),
    ],
)
def test_discover_dell_idrac_virtdisks(
    string_table: StringTable, expected_discoveries: set[str | None]
) -> None:
    parsed = parse_dell_idrac_virtdisks(string_table)
    assert {
        service.item for service in discover_dell_idrac_virtdisks(parsed)
    } == expected_discoveries


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "System",
            [
                Result(state=State.OK, summary="Raid level: Raid-5"),
                Result(state=State.OK, summary="Disk status: online"),
                Result(state=State.OK, summary="Component status: OK"),
                Result(state=State.OK, summary="Remaining redundancy: 1 physical disk(s)"),
            ],
        ),
        (
            "Backup",
            [
                Result(state=State.OK, summary="Raid level: Raid-6"),
                Result(state=State.CRIT, summary="Disk status: failed"),
                Result(state=State.CRIT, summary="Component status: critical"),
                Result(state=State.OK, summary="Remaining redundancy: 0 physical disk(s)"),
            ],
        ),
        (
            "Unknown",
            [],
        ),
    ],
)
def test_check_dell_idrac_virtdisks(item: str, expected_results: Sequence[Result]) -> None:
    parsed = parse_dell_idrac_virtdisks(_STRING_TABLE)
    assert list(check_dell_idrac_virtdisks(item, parsed)) == expected_results
