#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
raritan_pdu_ocprot_current_default_levels = (14.0, 15.0)

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
        ("C1", raritan_pdu_ocprot_current_default_levels),
        ("C2", raritan_pdu_ocprot_current_default_levels),
        ("C3", raritan_pdu_ocprot_current_default_levels),
        ("C4", raritan_pdu_ocprot_current_default_levels),
        ("C5", raritan_pdu_ocprot_current_default_levels),
        ("C6", raritan_pdu_ocprot_current_default_levels),
    ]
}

checks = {
    "": [
        (
            "C1",
            (14.0, 15.0),
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C2",
            (14.0, 15.0),
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C3",
            (14.0, 15.0),
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 7.00 A", [("current", 7.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C4",
            (14.0, 15.0),
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C5",
            (14.0, 15.0),
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
        (
            "C6",
            (14.0, 15.0),
            [
                (0, "Overcurrent protector is closed", []),
                (0, "Current: 0.00 A", [("current", 0.0, 14.0, 15.0, None, None)]),
            ],
        ),
    ]
}
