#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "dell_compellent_disks"

info = [
    [
        ["1", "1", "01-01", "1", "", "1"],
        ["2", "999", "01-02", "1", "", "1"],
        ["3", "1", "01-03", "999", "", "1"],
        ["4", "1", "01-04", "0", "ATTENTION", "1"],
        ["5", "1", "01-05", "999", "ATTENTION", "1"],
        ["10", "2", "01-10", "0", "KAPUTT", "1"],
    ],
    [
        ["1", "serial1"],
        ["2", "serial2"],
        ["3", "serial3"],
        ["4", "serial4"],
        ["5", "serial5"],
        ["10", "serial10"],
    ],
]

discovery = {
    "": [("01-01", {}), ("01-02", {}), ("01-03", {}), ("01-04", {}), ("01-05", {}), ("01-10", {})]
}

checks = {
    "": [
        (
            "01-01",
            {},
            [
                (0, "Status: UP", []),
                (0, "Location: Enclosure 1", []),
                (0, "Serial number: serial1", []),
            ],
        ),
        (
            "01-02",
            {},
            [
                (3, "Status: unknown[999]", []),
                (0, "Location: Enclosure 1", []),
                (0, "Serial number: serial2", []),
            ],
        ),
        (
            "01-03",
            {},
            [
                (0, "Status: UP", []),
                (0, "Location: Enclosure 1", []),
                (0, "Serial number: serial3", []),
            ],
        ),
        (
            "01-04",
            {},
            [
                (0, "Status: UP", []),
                (0, "Location: Enclosure 1", []),
                (0, "Serial number: serial4", []),
                (2, "Health: not healthy, Reason: ATTENTION", []),
            ],
        ),
        (
            "01-05",
            {},
            [
                (0, "Status: UP", []),
                (0, "Location: Enclosure 1", []),
                (0, "Serial number: serial5", []),
                (3, "Health: unknown[999], Reason: ATTENTION", []),
            ],
        ),
        (
            "01-10",
            {},
            [
                (2, "Status: DOWN", []),
                (0, "Location: Enclosure 1", []),
                (0, "Serial number: serial10", []),
                (2, "Health: not healthy, Reason: KAPUTT", []),
            ],
        ),
    ]
}
