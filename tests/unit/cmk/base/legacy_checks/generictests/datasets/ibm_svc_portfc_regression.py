#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_portfc"


info = [
    ["0", "1", "1", "fc", "8Gb", "1", "node1", "5005076803042126", "030400", "active", "switch"],
    [
        "1",
        "2",
        "2",
        "fc",
        "8Gb",
        "1",
        "node1",
        "5005076803082126",
        "040400",
        "active",
        "switch",
        "local_partner",
    ],
    [
        "2",
        "3",
        "3",
        "fc",
        "N/A",
        "1",
        "node1",
        "50050768030C2126",
        "000000",
        "inactive_unconfigured",
        "none",
    ],
    [
        "3",
        "4",
        "4",
        "fc",
        "N/A",
        "1",
        "node1",
        "5005076803102126",
        "000000",
        "inactive_unconfigured",
        "none",
    ],
    [
        "8",
        "1",
        "1",
        "fc",
        "8Gb",
        "2",
        "node2",
        "5005076803042127",
        "030500",
        "active",
        "switch",
        "local_partner",
    ],
    ["9", "2", "2", "fc", "8Gb", "2", "node2", "5005076803082127", "040500", "active", "switch"],
    [
        "10",
        "3",
        "3",
        "fc",
        "N/A",
        "2",
        "node2",
        "50050768030C2127",
        "000000",
        "inactive_unconfigured",
        "none",
    ],
    [
        "11",
        "4",
        "4",
        "fc",
        "N/A",
        "2",
        "node2",
        "5005076803102127",
        "000000",
        "inactive_unconfigured",
        "none",
        "local_partner",
    ],
]


discovery = {"": [("Port 0", None), ("Port 1", None), ("Port 8", None), ("Port 9", None)]}


checks = {
    "": [
        ("Port 0", {}, [(0, "Status: active, Speed: 8Gb, WWPN: 5005076803042126", [])]),
        ("Port 1", {}, [(0, "Status: active, Speed: 8Gb, WWPN: 5005076803082126", [])]),
        ("Port 8", {}, [(0, "Status: active, Speed: 8Gb, WWPN: 5005076803042127", [])]),
        ("Port 9", {}, [(0, "Status: active, Speed: 8Gb, WWPN: 5005076803082127", [])]),
    ]
}
