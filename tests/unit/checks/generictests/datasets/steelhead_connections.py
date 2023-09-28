#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "steelhead_connections"

info = [
    ["1.0", "1619"],
    ["2.0", "1390"],
    ["3.0", "0"],
    ["4.0", "4"],
    ["5.0", "1615"],
    ["6.0", "347"],
    ["7.0", "3009"],
]


discovery = {
    "": [(None, {})],
}


checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Total connections: 3009", []),
                (0, "Passthrough: 1390", [("passthrough", 1390)]),
                (0, "Optimized: 1619", []),
                (0, "Active: 347", [("active", 347)]),
                (0, "Established: 1615", [("established", 1615)]),
                (0, "Half opened: 0", [("halfOpened", 0)]),
                (0, "Half closed: 4", [("halfClosed", 4)]),
            ],
        ),
    ],
}
