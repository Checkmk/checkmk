#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "liebert_temp_general"


info = [
    [
        "Actual Supply Fluid Temp Set Point",
        "60.8",
        "deg F",
        "Ambient Air Temperature",
        "21.1",
        "def C",
    ],
    ["Free Cooling Utilization", "0.0", "%", "Return Fluid Temperature", "62.1", "deg F"],
    [
        "Supply Fluid Temperature",
        "57.2",
        "deg F",
        "Invalid Data for Testsing",
        "bogus value",
        "Unicycles",
    ],
]


discovery = {
    "": [
        ("Actual Supply Fluid Temp Set Point", {}),
        ("Ambient Air Temperature", {}),
        ("Free Cooling Utilization", {}),
        ("Return Fluid Temperature", {}),
        ("Supply Fluid Temperature", {}),
    ]
}


checks = {
    "": [
        (
            "Actual Supply Fluid Temp Set Point",
            {},
            [(0, "16.0 \xb0C", [("temp", 16.0, None, None, None, None)])],
        ),
        (
            "Ambient Air Temperature",
            {},
            [(0, "21.1 \xb0C", [("temp", 21.1, None, None, None, None)])],
        ),
        (
            "Free Cooling Utilization",
            {},
            [(0, "0.0 \xb0C", [("temp", 0.0, None, None, None, None)])],
        ),
        (
            "Return Fluid Temperature",
            {},
            [(0, "16.7 \xb0C", [("temp", 16.722222222222225, None, None, None, None)])],
        ),
        (
            "Supply Fluid Temperature",
            {},
            [(0, "14.0 \xb0C", [("temp", 14.000000000000002, None, None, None, None)])],
        ),
    ]
}
