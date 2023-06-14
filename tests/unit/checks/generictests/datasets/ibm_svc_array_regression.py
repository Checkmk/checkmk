#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_array"


info = [
    [
        "27",
        "SSD_mdisk27",
        "online",
        "1",
        "POOL_0_V7000_RZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
    [
        "28",
        "SSD_mdisk28",
        "online",
        "2",
        "POOL_1_V7000_BRZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
    [
        "29",
        "SSD_mdisk0",
        "online",
        "1",
        "POOL_0_V7000_RZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
    [
        "30",
        "SSD_mdisk1",
        "online",
        "2",
        "POOL_1_V7000_BRZ",
        "372.1GB",
        "online",
        "raid1",
        "1",
        "256",
        "generic_ssd",
    ],
]


discovery = {"": [("27", {}), ("28", {}), ("29", {}), ("30", {})]}


checks = {
    "": [
        ("27", {}, [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd", [])]),
        ("28", {}, [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd", [])]),
        ("29", {}, [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd", [])]),
        ("30", {}, [(0, "Status: online, RAID Level: raid1, Tier: generic_ssd", [])]),
    ]
}
