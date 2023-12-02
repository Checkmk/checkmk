#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "f5_bigip_fans"

info = [
    [
        ["1", "1", "15574"],
        ["2", "1", "16266"],
        ["3", "1", "15913"],
        ["4", "1", "16266"],
        ["5", "0", "0"],
        ["6", "1", "0"],
    ],
    [],
]

discovery = {
    "": [
        ("Chassis 1", {}),
        ("Chassis 2", {}),
        ("Chassis 3", {}),
        ("Chassis 4", {}),
        ("Chassis 5", {}),
        ("Chassis 6", {}),
    ]
}

checks = {
    "": [
        ("Chassis 1", {"lower": (2000, 500)}, [(0, "Speed: 15574 RPM", [])]),
        ("Chassis 5", {"lower": (2000, 500)}, [(2, "Speed: 0 RPM (warn/crit below 2000 RPM/500 RPM)", [])]),
        ("Chassis 6", {"lower": (2000, 500)}, [(0, "Fan Status: OK", [])]),
    ]
}
