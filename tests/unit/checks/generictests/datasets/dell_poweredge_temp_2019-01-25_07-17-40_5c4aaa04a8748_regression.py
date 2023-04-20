#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "dell_poweredge_temp"


info = [
    ["1", "1", "2", "3", "170", "System Board Inlet Temp", "470", "420", "30", "-70"],
    ["1", "2", "2", "3", "300", "System Board Exhaust Temp", "750", "700", "80", "30"],
    ["1", "3", "1", "2", "", "CPU1 Temp", "", "", "", ""],
    ["1", "4", "1", "2", "", "CPU2 Temp", "", "", "", ""],
]


discovery = {"": [("System Board Exhaust", {}), ("System Board Inlet", {})]}


checks = {
    "": [
        ("System Board Exhaust", {}, [(0, "30.0 \xb0C", [("temp", 30.0, 70.0, 75.0, None, None)])]),
        ("System Board Inlet", {}, [(0, "17.0 \xb0C", [("temp", 17.0, 42.0, 47.0, None, None)])]),
    ]
}
