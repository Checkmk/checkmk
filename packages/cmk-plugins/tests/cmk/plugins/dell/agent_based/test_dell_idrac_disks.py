#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import render, Result, State, StringTable
from cmk.plugins.dell.agent_based.dell_idrac_disks import (
    check_dell_idrac_disks,
    discover_dell_idrac_disks,
    parse_dell_idrac_disks,
)

# Row layout: (physicalDiskName, physicalDiskState, physicalDiskCapacityInMB,
#              physicalDiskSpareState, physicalDiskComponentStatus,
#              physicalDiskSmartAlertIndication, physicalDiskPowerState,
#              physicalDiskDisplayName)
_STRING_TABLE: StringTable = [
    ["Disk0", "3", "1024", "1", "3", "0", "1", "Disk 0 in slot"],
    ["Disk1", "7", "1024", "2", "5", "1", "2", "Disk 1 in slot"],
    ["", "3", "1024", "1", "3", "0", "1", "Empty disk"],
]
_SIZE_1024_MB = render.disksize(1024 * 1024 * 1024)


def test_parse_dell_idrac_disks() -> None:
    assert parse_dell_idrac_disks(_STRING_TABLE) == _STRING_TABLE


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            {"Disk0", "Disk1"},
        ),
        (
            [["Disk0", "3", "1024", "1", "3", "0", "1", "Disk 0 in slot"]],
            {
                "Disk0",
            },
        ),
    ],
)
def test_discover_dell_idrac_disks(
    string_table: StringTable, expected_discoveries: set[str | None]
) -> None:
    parsed = parse_dell_idrac_disks(string_table)
    assert {service.item for service in discover_dell_idrac_disks(parsed)} == expected_discoveries


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "Disk0",
            [
                Result(state=State.OK, summary=f"[Disk 0 in slot] Size: {_SIZE_1024_MB}"),
                Result(state=State.OK, summary="Disk state: online"),
                Result(state=State.OK, summary="Component state: OK"),
            ],
        ),
        (
            "Disk1",
            [
                Result(state=State.OK, summary=f"[Disk 1 in slot] Size: {_SIZE_1024_MB}"),
                Result(state=State.CRIT, summary="Disk state: failed"),
                Result(state=State.CRIT, summary="Component state: critical"),
                Result(state=State.CRIT, summary="Smart alert on disk"),
                Result(state=State.OK, summary="dedicated hotspare"),
                Result(state=State.WARN, summary="REBUILDING"),
            ],
        ),
        (
            "Unknown",
            [],
        ),
    ],
)
def test_check_dell_idrac_disks(item: str, expected_results: Sequence[Result]) -> None:
    parsed = parse_dell_idrac_disks(_STRING_TABLE)
    assert list(check_dell_idrac_disks(item, parsed)) == expected_results
