#!/usr/bin/env python3

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = 'raritan_px_outlets'

info = [[
    "3",
    "1",
    "3",
    "3",
    "3",
    "3",
    "3",
]]

discovery = {'': [("3", {})]}

checks = {
    '': [
        (
            '3',
            {},
            [
              (0, "Operational status: on", []),
              (0, "Voltage: 0.0 V", [("voltage", 0.003)]),
              (0, "Current: 0.0 A", [("current", 0.003)]),
              (0, "Power: 3.0 W", [("power", 3.0)]),
              (0, "Apparent Power: 3.0 VA", [("appower", 3.0)]),
              (0, "Energy: 3.0 Wh", [("energy", 3.0)]),
            ]
        )
    ],
}
