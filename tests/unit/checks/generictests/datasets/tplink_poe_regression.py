#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = "tplink_poe"

info = [
    [["1"], ["49153"], ["49154"], ["49155"], ["49156"], ["49157"], ["49159"], ["49160"], ["49180"]],
    [
        ["1", "1", "300", "0", "0"],
        ["2", "1", "300", "0", "1"],
        ["3", "1", "300", "-10", "0"],
        ["4", "1", "300", "290", "2"],
        ["5", "1", "300", "36", "2"],
        ["6", "1", "300", "0", "2"],
        ["7", "1", "300", "0", "8"],
        ["8", "1", "300", "39", "2"],
        ["9", "1", "300", "0", "10"],
    ],
]

discovery = {
    "": [
        ("1", {}),
        ("49153", {}),
        ("49154", {}),
        ("49155", {}),
        ("49156", {}),
        ("49157", {}),
        ("49159", {}),
        ("49160", {}),
        ("49180", {}),
    ]
}

checks = {
    "": [
        ("1", {}, [(0, "Operational status of the PSE is OFF", [])]),
        ("49153", {}, [(0, "Operational status of the PSE is OFF", [])]),
        (
            "49154",
            {},
            [
                (
                    3,
                    "Device returned faulty data: nominal power: 30.0, power consumption: -1.0, operational status: PoeStatus.OFF",
                    [],
                )
            ],
        ),
        (
            "49155",
            {},
            [
                (
                    2,
                    "POE usage (29.0W/30.0W): : 96.67% (warn/crit at 90.00%/95.00%)",
                    [("power_usage_percentage", 96.66666666666667, 90.0, 95.0, None, None)],
                )
            ],
        ),
        (
            "49156",
            {},
            [
                (
                    0,
                    "POE usage (3.6W/30.0W): : 12.00%",
                    [("power_usage_percentage", 12.000000000000002, 90.0, 95.0, None, None)],
                )
            ],
        ),
        (
            "49157",
            {},
            [
                (
                    0,
                    "POE usage (0.0W/30.0W): : 0%",
                    [("power_usage_percentage", 0.0, 90.0, 95.0, None, None)],
                )
            ],
        ),
        ("49159", {}, [(2, "Operational status of the PSE is FAULTY (hardware-fault)", [])]),
        (
            "49160",
            {},
            [
                (
                    0,
                    "POE usage (3.9W/30.0W): : 13.00%",
                    [("power_usage_percentage", 13.0, 90.0, 95.0, None, None)],
                )
            ],
        ),
        ("49180", {}, [(2, "Operational status of the PSE is FAULTY", [])]),
    ]
}
