#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ucs_c_rack_server_topsystem"


info = [
    [
        "topSystem",
        "dn sys",
        "address 192.168.1.1",
        "currentTime Wed Feb  6 09:12:12 2019",
        "mode stand-alone",
        "name CIMC-istreamer2a-etn",
    ]
]


discovery = {"": [(None, None)]}


checks = {
    "": [
        (
            None,
            {},
            [
                (0, "DN: sys", []),
                (0, "IP: 192.168.1.1", []),
                (0, "Mode: stand-alone", []),
                (0, "Name: CIMC-istreamer2a-etn", []),
                (0, "Date and time: 2019-02-06 09:12:12", []),
            ],
        )
    ]
}
