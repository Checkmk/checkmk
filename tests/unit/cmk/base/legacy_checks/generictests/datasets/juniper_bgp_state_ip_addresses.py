#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "juniper_bgp_state"

info = [
    [
        "4",
        "1",
        ["222", "173", "190", "239", "0", "64", "1", "17", "0", "0", "0", "0", "0", "0", "0", "1"],
    ],
    ["4", "2", ["0"] * 16],
]

discovery = {"": [("[dead:beef:40:111::1]", {}), ("[::]", {})]}

checks = {
    "": [
        (
            "[dead:beef:40:111::1]",
            {},
            [
                (0, "Status with peer [dead:beef:40:111::1] is opensent", []),
                (1, "operational status: halted", []),
            ],
        ),
        (
            "[::]",
            {},
            [
                (2, "Status with peer [::] is opensent", []),
                (0, "operational status: running", []),
            ],
        ),
    ]
}
