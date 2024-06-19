#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated

checkname = "ucs_bladecenter_psu"

info = [
    [
        "equipmentPsuInputStats",
        "Dn sys/switch-A/psu-2/input-stats",
        "Current 0.625000",
        "PowerAvg 142.333344",
        "Voltage 228.000000",
    ],
    [
        "equipmentPsuInputStats",
        "Dn sys/switch-A/psu-1/input-stats",
        "Current 0.562500",
        "PowerAvg 132.431259",
        "Voltage 236.000000",
    ],
    [
        "equipmentPsuInputStats",
        "Dn sys/switch-B/psu-2/input-stats",
        "Current 0.625000",
        "PowerAvg 142.670456",
        "Voltage 228.500000",
    ],
    [
        "equipmentPsuStats",
        "Dn sys/chassis-1/psu-1/stats",
        "AmbientTemp 17.000000",
        "Output12vAvg 12.008000",
        "Output3v3Avg 3.336000",
    ],
]

discovery = {
    "": [("Chassis 1 Module 1", {})],
    "chassis_temp": [("Ambient Chassis 1", {})],
    "switch_power": [
        ("Switch A Module 1", {}),
        ("Switch A Module 2", {}),
        ("Switch B Module 2", {}),
    ],
}

checks = {
    "": [
        (
            "Chassis 1 Module 1",
            {
                "levels_3v_upper": (3.4, 3.45),
                "levels_12v_upper": (12.1, 12.2),
                "levels_3v_lower": (3.25, 3.2),
                "levels_12v_lower": (11.9, 11.8),
            },
            [
                (0, "Output 3.3V-Average: 3.34 V", [("3_3v", 3.336, 3.4, 3.45, None, None)]),
                (0, "Output 12V-Average: 12.01 V", [("12v", 12.008, 12.1, 12.2, None, None)]),
            ],
        )
    ],
    "chassis_temp": [
        (
            "Ambient Chassis 1",
            {"levels": (35, 40)},
            [
                (0, "Sensors: 1", []),
                (0, "Highest: 17.0 \xb0C", [("temp", 17.0, None, None, None, None)]),
                (0, "Average: 17.0 \xb0C", []),
                (0, "Lowest: 17.0 \xb0C", []),
            ],
        )
    ],
    "switch_power": [
        (
            "Switch A Module 1",
            {},
            [
                (0, "Voltage: 236.0 V", [("voltage", 236.0, None, None, None, None)]),
                (0, "Current: 0.6 A", [("current", 0.5625, None, None, None, None)]),
                (0, "Power: 132.4 W", [("power", 132.431259, None, None, None, None)]),
            ],
        ),
        (
            "Switch A Module 2",
            {},
            [
                (0, "Voltage: 228.0 V", [("voltage", 228.0, None, None, None, None)]),
                (0, "Current: 0.6 A", [("current", 0.625, None, None, None, None)]),
                (0, "Power: 142.3 W", [("power", 142.333344, None, None, None, None)]),
            ],
        ),
        (
            "Switch B Module 2",
            {},
            [
                (0, "Voltage: 228.5 V", [("voltage", 228.5, None, None, None, None)]),
                (0, "Current: 0.6 A", [("current", 0.625, None, None, None, None)]),
                (0, "Power: 142.7 W", [("power", 142.670456, None, None, None, None)]),
            ],
        ),
    ],
}
