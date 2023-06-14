#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "alcatel_power_aos7"


info = [
    ["1", "1", "1"],
    ["2", "2", "1"],
    ["3", "3", "1"],
    ["4", "4", "1"],
    ["5", "5", "0"],
    ["6", "6", "0"],
    ["7", "7", "0"],
    ["8", "8", "2"],
    ["9", "9", "2"],
    ["10", "10", "2"],
]


discovery = {"": [("1", {}), ("10", {}), ("2", {}), ("3", {}), ("4", {}), ("8", {}), ("9", {})]}


checks = {
    "": [
        ("1", {}, [(0, "[AC] Status: up", [])]),
        ("10", {}, [(2, "[DC] Status: power save", [])]),
        ("2", {}, [(2, "[AC] Status: down", [])]),
        ("3", {}, [(2, "[AC] Status: testing", [])]),
        ("4", {}, [(2, "[AC] Status: unknown", [])]),
        ("8", {}, [(2, "[DC] Status: master", [])]),
        ("9", {}, [(2, "[DC] Status: idle", [])]),
    ]
}
