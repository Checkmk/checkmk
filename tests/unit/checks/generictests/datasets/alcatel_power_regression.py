#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "alcatel_power"


info = [
    ["1", "1", "0"],
    ["2", "1", "1"],
    ["3", "1", ""],
    ["4", "1", "0"],
    ["5", "1", "1"],
    ["6", "1", ""],
    ["7", "2", "0"],
    ["8", "2", "1"],
    ["9", "2", ""],
    ["10", "2", "0"],
    ["11", "2", "1"],
    ["12", "2", ""],
]


discovery = {"": [("11", {}), ("2", {}), ("5", {}), ("8", {})]}


checks = {
    "": [
        ("11", {}, [(2, "[AC] Operational status: down", [])]),
        ("2", {}, [(0, "[AC] Operational status: up", [])]),
        ("5", {}, [(0, "[AC] Operational status: up", [])]),
        ("8", {}, [(2, "[AC] Operational status: down", [])]),
    ]
}
