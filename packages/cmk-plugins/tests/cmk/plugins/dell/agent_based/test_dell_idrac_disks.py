#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import render, Result, State, StringTable
from cmk.plugins.dell.agent_based.dell_idrac_disks import (
    check_dell_idrac_disks,
    ComponentState,
    discover_dell_idrac_disks,
    Disk,
    DiskState,
    OperationState,
    parse_dell_idrac_disks,
    SpareState,
)

# Row layout: (physicalDiskNumber, physicalDiskName, physicalDiskState,
#              physicalDiskCapacityInMB, physicalDiskSpareState,
#              physicalDiskComponentStatus, physicalDiskSmartAlertIndication,
#              physicalDiskPowerState, physicalDiskDisplayName)
_STRING_TABLE: StringTable = [
    ["1", "Disk0", "3", "1024", "1", "3", "0", "1", "Disk 0 in slot"],
    ["2", "Disk1", "7", "1024", "2", "5", "1", "2", "Disk 1 in slot"],
    ["3", "", "3", "1024", "1", "3", "0", "1", "Empty disk"],
]
_SIZE_1024_MB = render.disksize(1024 * 1024 * 1024)


def test_parse_dell_idrac_disks() -> None:
    assert parse_dell_idrac_disks(_STRING_TABLE) == [
        Disk(
            1,
            "Disk0",
            DiskState("3"),
            capacity_MB=1024,
            spare_state=SpareState("1"),
            component_state=ComponentState("3"),
            smart_alert=False,
            operation_state=OperationState("1"),
            display_name="Disk 0 in slot",
        ),
        Disk(
            2,
            "Disk1",
            DiskState("7"),
            capacity_MB=1024,
            spare_state=SpareState("2"),
            component_state=ComponentState("5"),
            smart_alert=True,
            operation_state=OperationState("2"),
            display_name="Disk 1 in slot",
        ),
        Disk(
            3,
            "",
            DiskState("3"),
            capacity_MB=1024,
            spare_state=SpareState("1"),
            component_state=ComponentState("3"),
            smart_alert=False,
            operation_state=OperationState("1"),
            display_name="Empty disk",
        ),
    ]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            {"Disk0", "Disk1", "noname-3"},
        ),
        (
            [["1", "Disk0", "3", "1024", "1", "3", "0", "1", "Disk 0 in slot"]],
            {"Disk0"},
        ),
    ],
)
def test_discover_dell_idrac_disks(
    string_table: StringTable, expected_discoveries: set[str | None]
) -> None:
    parsed = parse_dell_idrac_disks(string_table)
    assert {service.item for service in discover_dell_idrac_disks(parsed)} == expected_discoveries


_DISK0_RESULTS = [
    Result(state=State.OK, summary=f"[Disk 0 in slot] Size: {_SIZE_1024_MB}"),
    Result(state=State.OK, summary="Disk state: online"),
    Result(state=State.OK, summary="Component state: ok"),
    Result(state=State.OK, summary="Spare state: not a spare"),
    Result(state=State.OK, summary="Operation state: not-applicable"),
]
_DISK1_RESULTS = [
    Result(state=State.OK, summary=f"[Disk 1 in slot] Size: {_SIZE_1024_MB}"),
    Result(state=State.CRIT, summary="Disk state: failed"),
    Result(state=State.CRIT, summary="Component state: critical"),
    Result(state=State.CRIT, summary="Smart alert on disk"),
    Result(state=State.OK, summary="Spare state: dedicated hot spare"),
    Result(state=State.WARN, summary="Operation state: rebuild"),
]
_EMPTY_DISK_RESULTS = [
    Result(state=State.OK, summary=f"[Empty disk] Size: {_SIZE_1024_MB}"),
    Result(state=State.OK, summary="Disk state: online"),
    Result(state=State.OK, summary="Component state: ok"),
    Result(state=State.OK, summary="Spare state: not a spare"),
    Result(state=State.OK, summary="Operation state: not-applicable"),
]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        ("Disk0", _DISK0_RESULTS),
        ("Disk1", _DISK1_RESULTS),
        ("noname-3", _EMPTY_DISK_RESULTS),
        ("Unknown", []),
        ("999", []),
    ],
)
def test_check_dell_idrac_disks(item: str, expected_results: Sequence[Result]) -> None:
    parsed = parse_dell_idrac_disks(_STRING_TABLE)
    assert list(check_dell_idrac_disks(item, parsed)) == expected_results
