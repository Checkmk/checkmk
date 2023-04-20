#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = "tplink_poe_summary"

info = [["900"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"levels": (90.0, 100.0)},
            [
                (
                    1,
                    "90.00 Watt (warn/crit at 90.00 Watt/100.00 Watt)",
                    [("power", 90.0, 90.0, 100.0)],
                )
            ],
        )
    ]
}
