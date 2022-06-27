#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = "prism_alerts"

info = [
    ['["timestamp", "message", "severity"]'],
    ['["1456749413140000", "DIMM fault detected on host 172.25.209.110. The node is running with 384 GiB whereas 512 GiB was installed.", "kCritical"]'],
    ['["1456749413150000", "Some warning message.", "kWarning"]'],
    ['["1456749413160000", "Some info message.", "kInfo"]'],
]

discovery = {"": [(None, {})]}

checks = {
    "": [(
        None,
        {},
        [
            (2, "3 alerts", []),
            (0,
             "Last worst on Mon Feb 29 13:36:53 2016: 'DIMM fault detected on host 172.25.209.110. The node is running with 384 GiB whereas 512 GiB was installed.'",
             []),
        ],
    ),]
}
