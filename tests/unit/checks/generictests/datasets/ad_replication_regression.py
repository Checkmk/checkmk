#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "ad_replication"

freeze_time = "2015-07-12 00:00:00"

info = [
    [
        "showrepl_COLUMNS,Destination",
        "DSA",
        "Site,Destination",
        "DSA,Naming",
        "Context,Source",
        "DSA",
        "Site,Source",
        "DSA,Transport",
        "Type,Number",
        "of",
        "Failures,Last",
        "Failure",
        "Time,Last",
        "Success",
        "Time,Last",
        "Failure",
        "Status",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        "09:15:37,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        "09:18:37,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        "09:18:37,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        "09:18:38,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        "09:18:52,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        "09:18:55,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        "09:19:00,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        "09:19:01,0",
    ],
    ["showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS003,RPC,0,0,2015-07-07", "08:48:03,0"],
    ["showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS055,RPC,0,0,2015-07-07", "08:48:03,0"],
    ["showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS008,RPC,0,0,2015-07-07", "08:48:03,0"],
]

discovery = {
    "": [
        ("HAM/SADS003", {}),
        ("HAM/SADS008", {}),
        ("HAM/SADS015", {}),
        ("HAM/SADS055", {}),
    ]
}

checks = {
    "": [
        ("HAM/SADS003", {"failure_levels": (15, 20)}, [(0, "All replications are OK.", [])]),
        (
            "HAM/SADS015",
            {"failure_levels": (-1, 2)},
            [
                (1, "Replications with failures: 3, Total failures: 0", []),
                (
                    0,
                    '\nHAM/SADS015 replication of context "CN=Configuration;DC=internal" reached  the threshold of maximum failures (-1) (Last success: 4 days 16 hours ago, Last failure: unknown, Num failures: 0, Status: 0)(!)\nHAM/SADS015 replication of context "CN=Schema;CN=Configuration;DC=internal" reached  the threshold of maximum failures (-1) (Last success: 4 days 17 hours ago, Last failure: unknown, Num failures: 0, Status: 0)(!)\nHAM/SADS015 replication of context "DC=network;DC=internal" reached  the threshold of maximum failures (-1) (Last success: 4 days 16 hours ago, Last failure: unknown, Num failures: 0, Status: 0)(!)',
                    [],
                ),
            ],
        ),
    ]
}
