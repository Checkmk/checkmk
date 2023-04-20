#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore
checkname = "hp_proliant_power"

info = [["2", "268"]]

discovery = {"": [(None, None)]}

checks = {
    "": [
        (None, {}, [(0, "Current reading: 268.00 Watts", [("watt", 268, None, None, None, None)])])
    ]
}
