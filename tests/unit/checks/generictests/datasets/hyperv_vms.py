#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


from cmk.base.legacy_checks.hyperv_vms import DEFAULT_PARAMETERS

checkname = "hyperv_vms"


info = [
    ['"Name"', '"State"', '"Uptime"', '"Status"'],
    ["Q-WSUS", "Running", "4.21:44:29", "Operating normally"],
    ['"AUN-CAA"', '"Off"', '"00:00:00"', '"Operating normally"'],
    ["weg-ca-webserver", "Wrong", "00:00:00", "Operating normally"],
    ["z4058044_snap (23.05.2014 - 09:29:29)", "Running", "18:20:34", "Operating normally"],
    ["z230897", "Stopping", "18:20:34", "VM crashed"],
    ["hlv2", "UnknownState", "00:00:00", "Totally normal"],
    ["hlv3", "Running", "00:00:00", "Operating normally"],
    ["& : File C:\\Program Files (x86)\\check_mk\\plugins\\windows_os_bonding.ps1 cannot"],
    [""],
]


discovery = {
    "": [
        ("Q-WSUS", {"discovered_state": "Running"}),
        ("AUN-CAA", {"discovered_state": "Off"}),
        ("weg-ca-webserver", {"discovered_state": "Wrong"}),
        ("z4058044_snap (23.05.2014 - 09:29:29)", {"discovered_state": "Running"}),
        ("z230897", {"discovered_state": "Stopping"}),
        ("hlv2", {"discovered_state": "UnknownState"}),
        ("hlv3", {"discovered_state": "Running"}),
    ]
}


checks = {
    "": [
        (
            "Q-WSUS",
            {"discovered_state": "Running", **DEFAULT_PARAMETERS},
            [(0, "State is Running (Operating normally)")],
        ),
        ("AUN-CAA", {"state": "Off", **DEFAULT_PARAMETERS}, [(1, "State is Off (Operating normally)")]),
        (
            "weg-ca-webserver",
            {"discovered_state": "Wrong", **DEFAULT_PARAMETERS},
            [(3, "Unknown state Wrong (Operating normally)")],
        ),
        (
            "z4058044_snap (23.05.2014 - 09:29:29)",
            {"discovered_state": "Running", **DEFAULT_PARAMETERS, "vm_target_state": ("discovery", True)},
            [(0, "State Running (Operating normally) matches discovery")],
        ),
        (
            "z230897",
            {"discovered_state": "Running", **DEFAULT_PARAMETERS, "vm_target_state": ("discovery", True)},
            [(2, "State Stopping (VM crashed) does not match discovery (Running)")],
        ),
        (
            "hlv2",
            {"discovered_state": "UnknownState", **DEFAULT_PARAMETERS, "vm_target_state": ("discovery", True)},
            [(0, "State UnknownState (Totally normal) matches discovery")],
        ),
        (
            "hlv3",
            {**DEFAULT_PARAMETERS, "vm_target_state": ("discovery", True)},
            [(3, "State is Running (Operating normally), discovery state is not available")],
        ),
    ]
}
