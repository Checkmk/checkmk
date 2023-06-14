#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "stulz_humidity"


info = [
    ["MICOS11Q", "12", "229376", "15221", "15221", "NO"],
    ["MICOS11Q", "12", "229376", "15221", "15221"],
]


discovery = {
    "": [
        ("MICOS11Q", (35, 40, 60, 65)),
        ("MICOS11Q", (35, 40, 60, 65)),
    ]
}


checks = {
    "": [
        (
            "MICOS11Q",
            (35, 40, 60, 65),
            [(2, "1.20% (warn/crit below 40.00%/35.00%)", [("humidity", 1.2, 60, 65, 0, 100)])],
        ),
        (
            "MICOS11Q",
            (35, 40, 60, 65),
            [(2, "1.20% (warn/crit below 40.00%/35.00%)", [("humidity", 1.2, 60, 65, 0, 100)])],
        ),
    ]
}
