#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = "apc_symmetra"

info = [
    [],
    [
        [
            "1",
            "2",
            "2",
            "100",
            "2",
            "0",
            "366000",
            "2",
            "06/20/2012",
            "18",
            "0",
            "0001010000000000001000000000000000000000000000000000000000000000",
        ]
    ],
]

discovery = {"": [(None, {})], "elphase": [("Battery", {})], "temp": [("Battery", {})]}

checks = {
    "": [
        (
            None,
            {"capacity": (95, 80), "calibration_state": 0, "battery_replace_state": 1},
            [
                (0, "Battery status: normal", []),
                (1, "Battery needs replacing", []),
                (0, "Output status: on line (calibration invalid)", []),
                (0, "Capacity: 100%", [("capacity", 100, 95, 80, 0, 100)]),
                (0, "Time remaining: 1 hour 1 minute", [("runtime", 61.0, None, None, None, None)]),
            ],
        ),
        (
            None,
            {"capacity": (95, 80), "calibration_state": 0, "battery_replace_state": 2},
            [
                (0, "Battery status: normal", []),
                (2, "Battery needs replacing", []),
                (0, "Output status: on line (calibration invalid)", []),
                (0, "Capacity: 100%", [("capacity", 100, 95, 80, 0, 100)]),
                (0, "Time remaining: 1 hour 1 minute", [("runtime", 61.0, None, None, None, None)]),
            ],
        ),
    ],
    "elphase": [
        (
            "Battery",
            {"current": (1, 1)},
            [(0, "Current: 0.0 A", [("current", 0.0, 1, 1, None, None)])],
        )
    ],
    "temp": [
        ("Battery", {"levels": (50, 60)}, [(0, "18.0 \xb0C", [("temp", 18.0, 50, 60, None, None)])])
    ],
}
