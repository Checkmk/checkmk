#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.hyperv_vms import (
    check_hyperv_vms,
    inventory_hyperv_vms,
    parse_hyperv_vms,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [
                ("Q-WSUS", {"discovered_state": "Running"}),
                ("AUN-CAA", {"discovered_state": "Off"}),
                ("weg-ca-webserver", {"discovered_state": "Wrong"}),
                ("z4058044_snap (23.05.2014 - 09:29:29)", {"discovered_state": "Running"}),
                ("z230897", {"discovered_state": "Stopping"}),
                ("hlv2", {"discovered_state": "UnknownState"}),
                ("hlv3", {"discovered_state": "Running"}),
            ],
        ),
    ],
)
def test_inventory_hyperv_vms(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for hyperv_vms check."""
    parsed = parse_hyperv_vms(string_table)
    result = list(inventory_hyperv_vms(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Q-WSUS",
            {
                "discovered_state": "Running",
                "vm_target_state": (
                    "map",
                    {
                        "FastSaved": 0,
                        "FastSavedCritical": 2,
                        "FastSaving": 0,
                        "FastSavingCritical": 2,
                        "Off": 1,
                        "OffCritical": 2,
                        "Other": 3,
                        "Paused": 0,
                        "PausedCritical": 2,
                        "Pausing": 0,
                        "PausingCritical": 2,
                        "Reset": 1,
                        "ResetCritical": 2,
                        "Resuming": 0,
                        "ResumingCritical": 2,
                        "Running": 0,
                        "RunningCritical": 2,
                        "Saved": 0,
                        "SavedCritical": 2,
                        "Saving": 0,
                        "SavingCritical": 2,
                        "Starting": 0,
                        "StartingCritical": 2,
                        "Stopping": 1,
                        "StoppingCritical": 2,
                    },
                ),
            },
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [(0, "State is Running (Operating normally)")],
        ),
        (
            "AUN-CAA",
            {
                "state": "Off",
                "vm_target_state": (
                    "map",
                    {
                        "FastSaved": 0,
                        "FastSavedCritical": 2,
                        "FastSaving": 0,
                        "FastSavingCritical": 2,
                        "Off": 1,
                        "OffCritical": 2,
                        "Other": 3,
                        "Paused": 0,
                        "PausedCritical": 2,
                        "Pausing": 0,
                        "PausingCritical": 2,
                        "Reset": 1,
                        "ResetCritical": 2,
                        "Resuming": 0,
                        "ResumingCritical": 2,
                        "Running": 0,
                        "RunningCritical": 2,
                        "Saved": 0,
                        "SavedCritical": 2,
                        "Saving": 0,
                        "SavingCritical": 2,
                        "Starting": 0,
                        "StartingCritical": 2,
                        "Stopping": 1,
                        "StoppingCritical": 2,
                    },
                ),
            },
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [(1, "State is Off (Operating normally)")],
        ),
        (
            "weg-ca-webserver",
            {
                "discovered_state": "Wrong",
                "vm_target_state": (
                    "map",
                    {
                        "FastSaved": 0,
                        "FastSavedCritical": 2,
                        "FastSaving": 0,
                        "FastSavingCritical": 2,
                        "Off": 1,
                        "OffCritical": 2,
                        "Other": 3,
                        "Paused": 0,
                        "PausedCritical": 2,
                        "Pausing": 0,
                        "PausingCritical": 2,
                        "Reset": 1,
                        "ResetCritical": 2,
                        "Resuming": 0,
                        "ResumingCritical": 2,
                        "Running": 0,
                        "RunningCritical": 2,
                        "Saved": 0,
                        "SavedCritical": 2,
                        "Saving": 0,
                        "SavingCritical": 2,
                        "Starting": 0,
                        "StartingCritical": 2,
                        "Stopping": 1,
                        "StoppingCritical": 2,
                    },
                ),
            },
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [(3, "Unknown state Wrong (Operating normally)")],
        ),
        (
            "z4058044_snap (23.05.2014 - 09:29:29)",
            {"discovered_state": "Running", "vm_target_state": ("discovery", True)},
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [(0, "State Running (Operating normally) matches discovery")],
        ),
        (
            "z230897",
            {"discovered_state": "Running", "vm_target_state": ("discovery", True)},
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [(2, "State Stopping (VM crashed) does not match discovery (Running)")],
        ),
        (
            "hlv2",
            {"discovered_state": "UnknownState", "vm_target_state": ("discovery", True)},
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [(0, "State UnknownState (Totally normal) matches discovery")],
        ),
        (
            "hlv3",
            {"vm_target_state": ("discovery", True)},
            [
                ['"Name"', '"State"', '"Uptime"', '"Status"'],
                ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
                ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
                ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
                [
                    "z4058044_snap (23.05.2014 - 09:29:29)",
                    "Running",
                    "18:20:34",
                    "Operating normally",
                ],
                ["z230897", "Stopping", "18:20:34", "VM crashed"],
                ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
                ["hlv3", "Running", "00:00:00", "Operating normally"],
                [
                    "& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"
                ],
                [""],
            ],
            [(3, "State is Running (Operating normally), discovery state is not available")],
        ),
    ],
)
def test_check_hyperv_vms(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for hyperv_vms check."""
    parsed = parse_hyperv_vms(string_table)
    result = list(check_hyperv_vms(item, params, parsed))
    assert result == expected_results
