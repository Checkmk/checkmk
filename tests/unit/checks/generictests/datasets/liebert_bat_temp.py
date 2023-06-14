#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "liebert_bat_temp"


info = [
    ["37"],
]


discovery = {
    "": [
        ("Battery", (40, 50)),
    ],
}


checks = {
    "": [
        (
            "Battery",
            (30, 40),
            [
                (
                    1,
                    "37 \xb0C (warn/crit at 30/40 \xb0C)",
                    [
                        ("temp", 37.0, 30.0, 40.0, None, None),
                    ],
                ),
            ],
        ),
    ],
}
