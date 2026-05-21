#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "dell_idrac_fans"


info = [
    ["1", "1", "", "System Board Fan1A", "", "", "", ""],
    ["2", "2", "", "System Board Fan1B", "", "", "", ""],
    ["3", "10", "", "System Board Fan2A", "", "", "", ""],
    # OK fan with only a subset of thresholds populated (upper warn + lower crit).
    # Regression for a crash caused by int("") on the empty threshold columns.
    ["4", "3", "7912", "FAN1A", "21500", "", "8000", ""],
    # OK fan with no thresholds at all — exercises the empty-params branch.
    ["5", "3", "7000", "FAN2A", "", "", "", ""],
]


discovery = {"": [("3", {}), ("4", {}), ("5", {})]}


checks = {
    "": [
        ("3", {}, [(2, "Status: FAILED, Name: System Board Fan2A", [])]),
        ("4", {}, [(0, "Status: OK, Name: FAN1A", []), (1, "Speed: 7912 RPM (warn/crit below 8000 RPM/never)", [])]),
        ("5", {}, [(0, "Status: OK, Name: FAN2A", []), (0, "Speed: 7000 RPM", [])]),
    ]
}
