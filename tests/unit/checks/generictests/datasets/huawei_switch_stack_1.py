#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "huawei_switch_stack"

info = [
    [["1"]],
    [
        ["1", "1"],
        ["2", "3"],
        ["3", "2"],
        ["4", "2"],
        ["5", "4"],
    ],
]

discovery = {
    "": [
        ("1", {"expected_role": "master"}),
        ("2", {"expected_role": "slave"}),
        ("3", {"expected_role": "standby"}),
        ("4", {"expected_role": "standby"}),
        ("5", {"expected_role": "unknown"}),
    ]
}

checks = {
    "": [
        (
            "1",
            {"expected_role": "master"},
            [(0, "master", [])],
        ),
        (
            "2",
            {"expected_role": "slave"},
            [(0, "slave", [])],
        ),
        (
            "3",
            {"expected_role": "standby"},
            [(0, "standby", [])],
        ),
        (
            "4",
            {"expected_role": "slave"},
            [(2, "Unexpected role: standby (Expected: slave)", [])],
        ),
        (
            "5",
            {"expected_role": "unknown"},
            [(2, "unknown", [])],
        ),
    ]
}
