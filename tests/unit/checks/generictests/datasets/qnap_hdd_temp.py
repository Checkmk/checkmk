#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "qnap_hdd_temp"

info = [
    ["HDD1", "37 C/98 F"],
    ["HDD2", "32 C/89 F"],
    ["HDD3", "40 C/104 F"],
    ["HDD4", "39 C/102 F"],
    ["HDD5", "45 C/113 F"],
    ["HDD6", "43 C/109 F"],
]

discovery = {
    "": [("HDD1", {}), ("HDD2", {}), ("HDD3", {}), ("HDD4", {}), ("HDD5", {}), ("HDD6", {})]
}

checks = {
    "": [
        (
            "HDD1",
            {"levels": (40, 45)},
            [(0, "37.0 \xb0C", [("temp", 37.0, 40.0, 45.0, None, None)])],
        ),
        (
            "HDD2",
            {"levels": (40, 45)},
            [(0, "32.0 \xb0C", [("temp", 32.0, 40.0, 45.0, None, None)])],
        ),
        (
            "HDD3",
            {"levels": (40, 45)},
            [
                (
                    1,
                    "40.0 \xb0C (warn/crit at 40/45 \xb0C)",
                    [("temp", 40.0, 40.0, 45.0, None, None)],
                )
            ],
        ),
        (
            "HDD4",
            {"levels": (40, 45)},
            [(0, "39.0 \xb0C", [("temp", 39.0, 40.0, 45.0, None, None)])],
        ),
        (
            "HDD5",
            {"levels": (40, 45)},
            [
                (
                    2,
                    "45.0 \xb0C (warn/crit at 40/45 \xb0C)",
                    [("temp", 45.0, 40.0, 45.0, None, None)],
                )
            ],
        ),
        (
            "HDD6",
            {"levels": (40, 45)},
            [
                (
                    1,
                    "43.0 \xb0C (warn/crit at 40/45 \xb0C)",
                    [("temp", 43.0, 40.0, 45.0, None, None)],
                )
            ],
        ),
    ]
}
