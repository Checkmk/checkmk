#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.dell.agent_based.dell_idrac_virtdisks import (
    check_dell_idrac_virtdisks,
    ComponentState,
    discover_dell_idrac_virtdisks,
    DiskState,
    parse_dell_idrac_virtdisks,
    RaidType,
    VirtualDisk,
)

# Row layout: (virtualDiskNumber, virtualDiskName, virtualDiskState,
#              virtualDiskLayout/raidLevel, virtualDiskComponentStatus,
#              virtualDiskRemainingRedundancy)
_STRING_TABLE: StringTable = [
    ["1", "System", "2", "4", "3", "1"],
    ["2", "Backup", "3", "5", "5", "0"],
    ["3", "", "2", "4", "3", "1"],
]


def test_parse_dell_idrac_virtdisks() -> None:
    assert parse_dell_idrac_virtdisks(_STRING_TABLE) == {
        "System": VirtualDisk(1, "System", DiskState("2"), RaidType("4"), ComponentState("3"), 1),
        "Backup": VirtualDisk(2, "Backup", DiskState("3"), RaidType("5"), ComponentState("5"), 0),
        "noname-3": VirtualDisk(3, "", DiskState("2"), RaidType("4"), ComponentState("3"), 1),
    }


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            {"System", "Backup", "noname-3"},
        ),
        (
            [["1", "System", "2", "4", "3", "1"]],
            {"System"},
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


_SYSTEM_RESULTS = [
    Result(state=State.OK, summary="Raid level: Raid-5"),
    Result(state=State.OK, summary="Disk status: online"),
    Result(state=State.OK, summary="Component status: ok"),
    Result(state=State.OK, summary="Remaining redundancy: 1 physical disk(s)"),
]
_BACKUP_RESULTS = [
    Result(state=State.OK, summary="Raid level: Raid-6"),
    Result(state=State.CRIT, summary="Disk status: failed"),
    Result(state=State.CRIT, summary="Component status: critical"),
    Result(state=State.OK, summary="Remaining redundancy: 0 physical disk(s)"),
]
_EMPTY_RESULTS = [
    Result(state=State.OK, summary="Raid level: Raid-5"),
    Result(state=State.OK, summary="Disk status: online"),
    Result(state=State.OK, summary="Component status: ok"),
    Result(state=State.OK, summary="Remaining redundancy: 1 physical disk(s)"),
]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        ("System", _SYSTEM_RESULTS),
        ("Backup", _BACKUP_RESULTS),
        ("noname-3", _EMPTY_RESULTS),
        ("Unknown", []),
        ("999", []),
    ],
)
def test_check_dell_idrac_virtdisks(item: str, expected_results: Sequence[Result]) -> None:
    parsed = parse_dell_idrac_virtdisks(_STRING_TABLE)
    assert list(check_dell_idrac_virtdisks(item, parsed)) == expected_results
