#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

checkname = "arista_bgp"

info = [
    [
        [
            [192, 168, 4, 4],
            [10, 60, 225, 123],
            "65000",
            [192, 168, 92, 0],
            "2",
            "6",
            "",
            "1.1.4.192.168.4.5",
        ],
        [
            [192, 168, 4, 28],
            [10, 60, 225, 123],
            "65008",
            [192, 168, 92, 0],
            "2",
            "6",
            "",
            "1.1.4.192.168.4.29",
        ],
        [
            [192, 168, 92, 0],
            [10, 60, 225, 123],
            "65060",
            [10, 60, 225, 124],
            "2",
            "6",
            "Cease/administrative reset",
            "1.1.4.192.168.92.1",
        ],
    ]
]

discovery = {"": [("192.168.4.29", {}), ("192.168.4.5", {}), ("192.168.92.1", {})]}

checks = {
    "": [
        (
            "192.168.4.29",
            {},
            [
                (0, "Local address: '192.168.4.28'", []),
                (0, "Local identifier: '10.60.225.123'", []),
                (0, "Remote AS number: 65008", []),
                (0, "Remote identifier: '192.168.92.0'", []),
                (0, "Admin state: 'running'", []),
                (0, "Peer state: 'established'", []),
                (0, "Last received error: ''", []),
                (0, "BGP version: 4", []),
                (0, "Remote address: '192.168.4.29'", []),
            ],
        ),
        (
            "192.168.4.5",
            {},
            [
                (0, "Local address: '192.168.4.4'", []),
                (0, "Local identifier: '10.60.225.123'", []),
                (0, "Remote AS number: 65000", []),
                (0, "Remote identifier: '192.168.92.0'", []),
                (0, "Admin state: 'running'", []),
                (0, "Peer state: 'established'", []),
                (0, "Last received error: ''", []),
                (0, "BGP version: 4", []),
                (0, "Remote address: '192.168.4.5'", []),
            ],
        ),
        (
            "192.168.92.1",
            {},
            [
                (0, "Local address: '192.168.92.0'", []),
                (0, "Local identifier: '10.60.225.123'", []),
                (0, "Remote AS number: 65060", []),
                (0, "Remote identifier: '10.60.225.124'", []),
                (0, "Admin state: 'running'", []),
                (0, "Peer state: 'established'", []),
                (0, "Last received error: 'Cease/administrative reset'", []),
                (0, "BGP version: 4", []),
                (0, "Remote address: '192.168.92.1'", []),
            ],
        ),
    ]
}
