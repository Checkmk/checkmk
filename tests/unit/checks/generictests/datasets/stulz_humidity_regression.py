#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated


checkname = "stulz_humidity"


# OIDEnd is "{bus}.{unit}.{subindex}"; the device exposes units on two buses.
# Readings are in per-mille and divided by 10 by the check.
info = [
    ["1.1.1", "339"],
    ["1.2.1", "332"],
    ["2.1.1", "500"],
    ["2.2.1", "308"],
]


discovery = {
    "": [
        ("1-1", {}),
        ("1-2", {}),
        ("2-1", {}),
        ("2-2", {}),
    ]
}


checks = {
    "": [
        (
            "1-1",
            {
                "levels_lower": (40.0, 35.0),
                "levels": (60.0, 65.0),
            },
            [(2, "33.90% (warn/crit below 40.00%/35.00%)", [("humidity", 33.9, 60, 65, 0, 100)])],
        ),
        (
            "2-1",
            {
                "levels_lower": (40.0, 35.0),
                "levels": (60.0, 65.0),
            },
            [(0, "50.00%", [("humidity", 50.0, 60, 65, 0, 100)])],
        ),
    ]
}
