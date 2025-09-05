#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "huawei_switch_mem"

info = [
    [
        ["67108867", "HUAWEI S6720 Routing Switch"],
        ["67108869", "Board slot 0"],
        ["68157445", "Board slot 1"],
        ["68157449", "MPU Board 1"],
        ["68173836", "Card slot 1/1"],
        ["68190220", "Card slot 1/2"],
        ["68239373", "POWER Card 1/PWR1"],
        ["68255757", "POWER Card 1/PWR2"],
        ["68272141", "FAN Card 1/FAN1"],
        ["69206021", "Board slot 2"],
        ["69222412", "Card slot 2/1"],
        ["69206025", "MPU Board 2"],
        ["69206045", "MPU Board 3"],
        ["69206055", "MPU Board 4"],  # Info missing in second array
    ],
    [
        ["67108867", "0"],
        ["67108869", "0"],
        ["68157445", "0"],
        ["68157449", "22"],
        ["68173836", "0"],
        ["68190220", "0"],
        ["68239373", "0"],
        ["68255757", "0"],
        ["68272141", "0"],
        ["69206021", "0"],
        ["69222412", "0"],
        ["69206025", "85"],
        ["69206045", "95"],
    ],
]

discovery = {
    "": [
        ("1", {}),
        ("2", {}),
        ("3", {}),
        ("4", {}),
    ]
}

checks = {
    "": [
        (
            "1",
            {"levels": (80.0, 90.0)},
            [
                (
                    0,
                    "Usage: 22.00%",
                    [("mem_used_percent", 22.0, 80.0, 90.0, None, None)],
                )
            ],
        ),
        (
            "2",
            {"levels": (80.0, 90.0)},
            [
                (
                    1,
                    "Usage: 85.00% (warn/crit at 80.00%/90.00%)",
                    [("mem_used_percent", 85.0, 80.0, 90.0, None, None)],
                )
            ],
        ),
        (
            "3",
            {"levels": (80.0, 90.0)},
            [
                (
                    2,
                    "Usage: 95.00% (warn/crit at 80.00%/90.00%)",
                    [("mem_used_percent", 95.0, 80.0, 90.0, None, None)],
                )
            ],
        ),
        (
            "4",
            {"levels": (80.0, 90.0)},
            [],
        ),
    ]
}
