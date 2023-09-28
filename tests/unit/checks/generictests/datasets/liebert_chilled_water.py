#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "liebert_chilled_water"


info = [
    [
        "Supply Chilled Water Over Temp",
        "Inactive Event",
        "Chilled Water Control Valve Failure",
        "Inactive Event",
        "Supply Chilled Water Loss of Flow",
        "Everything is on fire",
    ]
]


discovery = {
    "": [
        ("Supply Chilled Water Over Temp", {}),
        ("Chilled Water Control Valve Failure", {}),
        ("Supply Chilled Water Loss of Flow", {}),
    ],
}


checks = {
    "": [
        (
            "Supply Chilled Water Over Temp",
            {},
            [
                (0, "Normal", []),
            ],
        ),
        (
            "Supply Chilled Water Loss of Flow",
            {},
            [
                (2, "Everything is on fire", []),
            ],
        ),
    ],
}
