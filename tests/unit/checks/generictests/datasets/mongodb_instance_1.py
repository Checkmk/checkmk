#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

checkname = "mongodb_instance"

info = [
    ["mode", "Primary"],
    ["address", "idbv0068.ww-intern.de:27017"],
    ["version", "3.0.4"],
    ["pid", "1999"],
]

discovery = {
    "": [
        (None, None),
    ],
}

checks = {
    "": [
        (
            None,
            {},
            [
                (
                    0,
                    "Mode: Primary",
                ),
                (
                    0,
                    "Address: idbv0068.ww-intern.de:27017",
                ),
                (
                    0,
                    "Version: 3.0.4",
                ),
                (
                    0,
                    "Pid: 1999",
                ),
            ],
        ),
    ],
}
