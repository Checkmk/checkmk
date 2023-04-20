#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = "mknotifyd"

info = [
    ["1571212728"],
    ["[heute]"],
    ["Version:         2019.10.14"],
    ["Updated:         1571212726 (2019-10-16 09:58:46)"],
    ["Started:         1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Configuration:   1571143926 (2019-10-15 14:52:06, 68800 sec ago)"],
    ["Listening FD:    5"],
    ["Spool:           New"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Spool:           Deferred"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Spool:           Corrupted"],
    ["Count:           0"],
    ["Oldest:"],
    ["Youngest:"],
    ["Queue:           mail"],
    ["Waiting:         0"],
    ["Processing:      0"],
    ["Queue:           None"],
    ["Waiting:         0"],
    ["Processing:      0"],
    ["Connection:               127.0.0.1:49850"],
    ["Type:                     incoming"],
    ["State:                    established"],
    ["Since:                    1571143941 (2019-10-15 14:52:21, 68785 sec ago)"],
    ["Notifications Sent:       47"],
    ["Notifications Received:   47"],
    ["Pending Acknowledgements:"],
    ["Socket FD:                6"],
    ["HB. Interval:             10 sec"],
    ["LastIncomingData:         1571212661 (2019-10-16 09:57:41, 65 sec ago)"],
    ["LastHeartbeat:            1571212717 (2019-10-16 09:58:37, 9 sec ago)"],
    ["InputBuffer:              0 Bytes"],
    ["OutputBuffer:             0 Bytes"],
]

discovery = {
    "": [("heute", {})],
    "connection": [("heute-127.0.0.1", {})],
}

checks = {
    "": [
        (
            "heute",
            {},
            [
                (0, "Version: 2019.10.14", []),
                (
                    0,
                    "Spooler running",
                    [
                        ("last_updated", 2, None, None, None, None),
                        ("new_files", 0, None, None, None, None),
                    ],
                ),
            ],
        )
    ],
    "connection": [
        (
            "heute-127.0.0.1",
            {},
            [
                (0, "Alive", []),
                (0, "Uptime: 19 hours 6 minutes", []),
                (0, "47 Notifications sent", []),
                (0, "47 Notifications received", []),
            ],
        )
    ],
}
