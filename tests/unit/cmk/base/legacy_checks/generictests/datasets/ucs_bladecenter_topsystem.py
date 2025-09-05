#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "ucs_bladecenter_topsystem"

info = [
    [
        "topSystem",
        "Address 192.168.1.1",
        "CurrentTime 2015-07-15T16:40:27.600",
        "Ipv6Addr ::",
        "Mode cluster",
        "Name svie23ucsfi01",
        "SystemUpTime 125:16:10:53",
    ]
]

discovery = {"": [(None, None)]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "Address: 192.168.1.1", []),
                (0, "CurrentTime: 2015-07-15T16:40:27.600", []),
                (0, "Ipv6Addr: ::", []),
                (0, "Mode: cluster", []),
                (0, "Name: svie23ucsfi01", []),
                (0, "SystemUpTime: 125:16:10:53", []),
            ],
        )
    ]
}
