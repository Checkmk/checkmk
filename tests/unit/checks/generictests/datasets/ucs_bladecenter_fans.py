#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ucs_bladecenter_fans"


info = [
    [
        "equipmentNetworkElementFanStats",
        "Dn sys/switch-A/fan-module-1-1/fan-1/stats",
        "SpeedAvg 8542",
    ],
    ["equipmentFanModuleStats", "Dn sys/chassis-2/fan-module-1-1/stats", "AmbientTemp 29.000000"],
    [
        "equipmentFan",
        "Dn sys/chassis-1/fan-module-1-1/fan-1",
        "Model N20-FAN5",
        "OperState operable",
    ],
    ["equipmentFanStats", "Dn sys/chassis-2/fan-module-1-1/fan-1/stats", "SpeedAvg 3652"],
]


discovery = {"": [("Chassis 2", None), ("Switch A", None)], "temp": [("Ambient Chassis 2 FAN", {})]}


checks = {
    "": [
        ("Chassis 2", {}, [(3, "Fan statistics not available", [])]),
        ("Switch A", {}, [(3, "Fan statistics not available", [])]),
    ],
    "temp": [
        (
            "Ambient Chassis 2 FAN",
            {"levels": (40, 50)},
            [
                (0, "Sensors: 1", []),
                (0, "Highest: 29.0 \xb0C", [("temp", 29.0, None, None, None, None)]),
                (0, "Average: 29.0 \xb0C", []),
                (0, "Lowest: 29.0 \xb0C", []),
            ],
        )
    ],
}
