#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "raritan_pdu_ocprot"

info = [
    [
        ["1.1.1", "4", "0"],
        ["1.1.15", "1", "0"],
        ["1.2.1", "4", "0"],
        ["1.2.15", "1", "0"],
        ["1.3.1", "4", "70"],
        ["1.3.15", "1", "0"],
        ["1.4.1", "4", "0"],
        ["1.4.15", "1", "0"],
        ["1.5.1", "4", "0"],
        ["1.5.15", "1", "0"],
        ["1.6.1", "4", "0"],
        ["1.6.15", "1", "0"],
    ],
    [["1"], ["0"], ["1"], ["0"], ["1"], ["0"], ["1"], ["0"], ["1"], ["0"], ["1"], ["0"]],
]

discovery = {
    "": [
        ("C1", {}),
        ("C2", {}),
        ("C3", {}),
        ("C4", {}),
        ("C5", {}),
        ("C6", {}),
    ]
}

checks = {
    "": [
        (
            "C1",
            {"levels": (14.0, 15.0)},
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C2",
            {"levels": (14.0, 15.0)},
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C3",
            {"levels": (14.0, 15.0)},
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 7.00 A", [("current", 7.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C4",
            {"levels": (14.0, 15.0)},
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C5",
            {"levels": (14.0, 15.0)},
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C6",
            {"levels": (14.0, 15.0)},
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
    ]
}
