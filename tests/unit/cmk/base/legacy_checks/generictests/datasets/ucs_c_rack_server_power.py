#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ucs_c_rack_server_power"


info = [
    [
        "computeMbPowerStats",
        "dn sys/rack-unit-1/board/power-stats",
        "consumedPower 88",
        "inputCurrent 6.00",
        "inputVoltage 12.100",
    ],
    [
        "computeMbPowerStats",
        "dn sys/rack-unit-2/board/power-stats",
        "consumedPower 90",
        "inputCurrent 7.00",
        "inputVoltage 12.100",
    ],
]


discovery = {"": [("Rack Unit 1", {}), ("Rack Unit 2", {})]}


checks = {
    "": [
        (
            "Rack Unit 1",
            {"power_upper_levels": (90, 100)},
            [
                (0, "Power: 88.00 W", [("power", 88, 90.0, 100.0, None, None)]),
                (0, "Current: 6.0 A", []),
                (0, "Voltage: 12.1 V", []),
            ],
        ),
        (
            "Rack Unit 2",
            {"power_upper_levels": (90, 100)},
            [
                (
                    1,
                    "Power: 90.00 W (warn/crit at 90.00 W/100.00 W)",
                    [("power", 90, 90.0, 100.0, None, None)],
                ),
                (0, "Current: 7.0 A", []),
                (0, "Voltage: 12.1 V", []),
            ],
        ),
    ]
}
