#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "vutlan_ems_temp"

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
    ]
]

discovery = {"": [("Analog-1", {}), ("Analog-2", {}), ("Onboard Temperature", {})]}

checks = {
    "": [
        (
            "Analog-1",
            {"levels": (80.0, 90.0)},
            [(0, "22.0 °C", [("temp", 22.0, 80.0, 90.0, None, None)])],
        ),
        (
            "Analog-2",
            {"levels": (10.0, 20.0)},
            [(2, "22.1 °C (warn/crit at 10.0/20.0 °C)", [("temp", 22.1, 10.0, 20.0, None, None)])],
        ),
        (
            "Onboard Temperature",
            {"levels": (80.0, 90.0)},
            [(0, "32.8 °C", [("temp", 32.8, 80.0, 90.0, None, None)])],
        ),
    ]
}
