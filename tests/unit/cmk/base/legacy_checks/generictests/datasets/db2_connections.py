#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "db2_connections"

info = [
    ["[[[db2taddm:CMDBS1]]]"],
    ["port", "50214"],
    ["connections", "40"],
    ["latency", "0:1.03"],
    ["[[[db2taddm:CMDBS1de]]]"],
    ["port", "50213"],
    ["connections", "42"],
    ["latency", "0:1,03"],
]

discovery = {
    "": [
        ("db2taddm:CMDBS1", None),
        ("db2taddm:CMDBS1de", None),
    ],
}

checks = {
    "": [
        (
            "db2taddm:CMDBS1",
            {"levels_total": (150, 200)},
            [
                (0, "Connections: 40", [("connections", 40, 150, 200, None, None)]),
                (0, "Port: 50214", []),
                (0, "Latency: 1003.00 ms", [("latency", 1003, None, None, None, None)]),
            ],
        ),
        (
            "db2taddm:CMDBS1de",
            {"levels_total": (150, 200)},
            [
                (0, "Connections: 42", [("connections", 42, 150, 200, None, None)]),
                (0, "Port: 50213", []),
                (0, "Latency: 1003.00 ms", [("latency", 1003, None, None, None, None)]),
            ],
        ),
    ],
}
