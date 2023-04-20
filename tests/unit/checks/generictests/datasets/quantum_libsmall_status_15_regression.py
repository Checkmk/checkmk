#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = "quantum_libsmall_status"

info = [
    [
        ["1.0", "1"],
        ["2.0", "1"],
        ["3.0", "1"],
        ["4.0", "1"],
        ["5.0", "1"],
        ["6.0", "1"],
        ["7.0", "1"],
        ["8.0", "0"],
    ],
    [],
]

discovery = {"": [(None, None)]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Power: good", []),
                (0, "Cooling: good", []),
                (0, "Control: good", []),
                (0, "Connectivity: good", []),
                (0, "Robotics: good", []),
                (0, "Media: good", []),
                (0, "Drive: good", []),
                (0, "Operator action request: no", []),
            ],
        )
    ]
}
