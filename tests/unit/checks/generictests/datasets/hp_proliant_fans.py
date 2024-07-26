#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore
checkname = "hp_proliant_fans"

info = [
    ["1", "3", "3", "2", "2", ""],
    ["2", "3", "3", "2", "2", ""],
    ["3", "3", "3", "2", "2", ""],
    ["4", "3", "3", "2", "2", ""],
    ["5", "3", "3", "2", "2", ""],
    ["6", "3", "3", "2", "2", ""],
]

discovery = {
    "": [
        ("1 (system)", {}),
        ("2 (system)", {}),
        ("3 (system)", {}),
        ("4 (system)", {}),
        ("5 (system)", {}),
        ("6 (system)", {}),
    ]
}

checks = {
    "": [
        (
            "1 (system)",
            {},
            [
                (
                    0,
                    (
                        'FAN Sensor 1 "system", Speed is normal, State is ok\n'
                        "HPE started to report the speed in percent without updating the MIB.\n"
                        "This means that for a reported speed of 'other', 'normal' or 'high', "
                        "there is the chance that the speed is actually 1, 2 or 3 percent respectively.\n"
                        "This has no influence on the service state."

                    ),
                    [],
                ),
            ],
        ),
    ]
}
