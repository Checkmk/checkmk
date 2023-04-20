#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "vutlan_ems_leakage"

info = [
    [
        ["101001", "Dry-1", "0"],
        ["101002", "Dry-2", "0"],
        ["101003", "Dry-3", "0"],
        ["101004", "Dry-4", "0"],
        ["106001", "Analog-5", "0"],
        ["107001", "Analog-6", "0"],
        ["201001", "Onboard Temperature", "32.80"],
        ["201002", "Analog-1", "22.00"],
        ["201003", "Analog-2", "22.10"],
        ["202001", "Analog-3", "46.20"],
        ["202002", "Analog-4", "42.10"],
        ["203001", "Onboard Voltage DC", "12.06"],
        ["301001", "Analog Power", "on"],
        ["304001", "Power-1", "off"],
        ["304002", "Power-2", "off"],
        ["403001", "USB Web camera", "0"],
        ["107002", "Banana", "1"],
    ]
]

discovery = {"": [("Analog-6", {}), ("Banana", {})]}

checks = {
    "": [
        ("Analog-6", {}, [(0, "No leak detected", [])]),
        ("Banana", {}, [(2, "Leak detected", [])]),
    ]
}
