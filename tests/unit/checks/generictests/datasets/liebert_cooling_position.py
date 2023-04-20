#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "liebert_cooling_position"


info = [
    ["Free Cooling Valve Open Position", "42", "%"],
    ["This is ignored", "42", "%"],
]


discovery = {
    "": [
        ("Free Cooling Valve Open Position", {}),
    ],
}


checks = {
    "": [
        (
            "Free Cooling Valve Open Position",
            {"min_capacity": (50, 45)},
            [
                (
                    2,
                    "42.00 % (warn/crit below 50.00 %/45.00 %)",
                    [
                        ("capacity_perc", 42.0, None, None, None, None),
                    ],
                ),
            ],
        ),
    ],
}
