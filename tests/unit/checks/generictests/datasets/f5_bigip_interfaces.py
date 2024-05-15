#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "f5_bigip_interfaces"
mock_item_state = {
    "": {
        "in": (0, 439189486311),
        "out": (0, 375541323492),
    },
}


info = [
    ["1.1", "0", "439189486311", "375541323492"],
    ["1.2", "0", "121591230679", "201963958037"],
    ["1.3", "0", "434523103807", "413556383286"],
    ["1.4", "0", "1244059671", "991534207"],
    ["2.1", "5", "0", "0"],
    ["2.2", "5", "0", "0"],
    ["mgmt", "0", "21498688535", "3648383840"],
]

discovery = {
    "": [
        ("1.1", {}),
        ("1.2", {}),
        ("1.3", {}),
        ("1.4", {}),
        ("mgmt", {}),
    ]
}

checks = {
    "": [
        (
            "1.1",
            {},
            [
                (0, "Up", []),
                (0, "In bytes: 0.00 B/s", [("bytes_in", 0.0)]),
                (0, "Out bytes: 0.00 B/s", [("bytes_out", 0.0)]),
            ],
        ),
    ]
}
