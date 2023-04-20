#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "liebert_cooling"


info = [
    ["Cooling Capacity (Primary)", "42", "%"],
    ["Cooling Capacity (Secondary)", "42", "%"],
]


discovery = {
    "": [
        ("Cooling Capacity (Primary)", {}),
        ("Cooling Capacity (Secondary)", {}),
    ],
}


checks = {
    "": [
        (
            "Cooling Capacity (Primary)",
            {"min_capacity": (45, 40)},
            [
                (
                    1,
                    "42.00 % (warn/crit below 45.00 %/40.00 %)",
                    [
                        ("capacity_perc", 42.0, None, None),
                    ],
                ),
            ],
        ),
        (
            "Cooling Capacity (Secondary)",
            {"max_capacity": (41, 43)},
            [
                (
                    1,
                    "42.00 % (warn/crit at 41.00 %/43.00 %)",
                    [
                        ("capacity_perc", 42.0, 41.0, 43.0, None, None),
                    ],
                ),
            ],
        ),
    ],
}
