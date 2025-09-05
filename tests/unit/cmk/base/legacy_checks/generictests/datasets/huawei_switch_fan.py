#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "huawei_switch_fan"

info = [
    ["1.1", "50", "1"],
    ["1.2", "80", "1"],
    ["2.5", "50", "0"],
    ["2.7", "90", "1"],
]

discovery = {
    "": [
        ("1/1", {}),
        ("1/2", {}),
        ("2/2", {}),
    ]
}

checks = {
    "": [
        (
            "1/1",
            {},
            [(0, "50.00%", [("fan_perc", 50.0, None, None, None, None)])],
        ),
        (
            "1/2",
            {"levels": (70.0, 85.0)},
            [
                (
                    1,
                    "80.00% (warn/crit at 70.00%/85.00%)",
                    [("fan_perc", 80.0, 70.0, 85.0, None, None)],
                )
            ],
        ),
    ]
}
