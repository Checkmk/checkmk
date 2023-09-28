#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "juniper_bgp_state"

info = [
    ["6", "2", [100, 96, 1, 34]],
    ["3", "2", [100, 96, 1, 38]],
]

discovery = {
    "": [
        ("100.96.1.34", {}),
        ("100.96.1.38", {}),
    ]
}

checks = {
    "": [
        (
            "100.96.1.34",
            {},
            [
                (0, "Status with peer 100.96.1.34 is established", []),
                (0, "operational status: running", []),
            ],
        ),
        (
            "100.96.1.38",
            {},
            [
                (2, "Status with peer 100.96.1.38 is active", []),
                (0, "operational status: running", []),
            ],
        ),
    ]
}
