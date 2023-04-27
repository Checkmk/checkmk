#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "teracom_tcw241_analog"


info = [
    [
        ["Tank_Level", "80000", "10000"],
    ], [
        ["Motor_Temp", "70000", "37000"],
    ], [
        ["Analog Input 3", "60000", "0"],
    ], [
        ["Analog Input 4", "60000", "0"],
    ],
    [["48163", "39158", "33", "34"]],
]


discovery = {"": [("1", {}), ("2", {})]}


checks = {
    "": [
        (
            "2",
            {},
            [
                (
                    1,
                    "[Motor_Temp]: 39.16 V (warn/crit at 37.00 V/70.00 V)",
                    [("voltage", 39.158, 37.0, 70.0, None, None)],
                )
            ],
        ),
        (
            "1",
            {},
            [
                (
                    1,
                    "[Tank_Level]: 48.16 V (warn/crit at 10.00 V/80.00 V)",
                    [("voltage", 48.163, 10.0, 80.0, None, None)],
                )
            ],
        ),
    ]
}
