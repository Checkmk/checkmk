#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[name-defined]
# pylint: disable=undefined-variable

aggregation_rules["host"] = (
    "Host $HOST$",
    ["HOST"],
    "worst",
    [
        ("general", ["$HOST$"]),
        ("performance", ["$HOST$"]),
        ("filesystems", ["$HOST$"]),
        ("networking", ["$HOST$"]),
        ("applications", ["$HOST$"]),
        ("logfiles", ["$HOST$"]),
        ("hardware", ["$HOST$"]),
        ("other", ["$HOST$"]),
    ],
)

aggregation_rules["general"] = (
    "General State",
    ["HOST"],
    "worst",
    [
        ("$HOST$", HOST_STATE),
        ("$HOST$", "Uptime"),
        ("checkmk", ["$HOST$"]),
    ],
)

aggregation_rules["filesystems"] = (
    "Disk & Filesystems",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "Disk|MD"),
        ("multipathing", ["$HOST$"]),
        (FOREACH_SERVICE, "$HOST$", "fs_(.*)", "filesystem", ["$HOST$", "$1$"]),
    ],
)

aggregation_rules["filesystem"] = (
    "$FS$",
    ["HOST", "FS"],
    "worst",
    [
        ("$HOST$", "fs_$FS$$"),
        ("$HOST$", "Mount options of $FS$$"),
    ],
)

aggregation_rules["multipathing"] = (
    "Multipathing",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "Multipath"),
    ],
)

aggregation_rules["performance"] = (
    "Performance",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "CPU|Memory|Vmalloc|Kernel|Number of threads"),
    ],
)

aggregation_rules["hardware"] = (
    "Hardware",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "IPMI|RAID"),
    ],
)

aggregation_rules["networking"] = (
    "Networking",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "NFS|Interface|TCP"),
    ],
)

aggregation_rules["checkmk"] = (
    "Check_MK",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "Check_MK|Uptime"),
    ],
)

aggregation_rules["logfiles"] = (
    "Logfiles",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "LOG"),
    ],
)
aggregation_rules["applications"] = (
    "Applications",
    ["HOST"],
    "worst",
    [
        ("$HOST$", "ASM|ORACLE|proc"),
    ],
)

aggregation_rules["other"] = (
    "Other",
    ["HOST"],
    "worst",
    [
        ("$HOST$", REMAINING),
    ],
)

aggregations += [
    ("Hosts", FOREACH_HOST, ALL_HOSTS, "host", ["$1$"]),
]
