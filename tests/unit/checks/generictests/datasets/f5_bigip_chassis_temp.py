#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "f5_bigip_chassis_temp"

info = [["1", "30"], ["2", "32"], ["3", "36"], ["4", "41"], ["5", "41"]]

discovery = {
    "": [
        ("1", {}),
        ("2", {}),
        ("3", {}),
        ("4", {}),
        ("5", {}),
    ]
}

checks = {
    "": [
        ("1", {"levels": (35.0, 40.0)}, [(0, "30 °C", [("temp", 30, 35.0, 40.0, None, None)])]),
        (
            "3",
            {"levels": (35.0, 40.0)},
            [(1, "36 °C (warn/crit at 35.0/40.0 °C)", [("temp", 36, 35.0, 40.0, None, None)])],
        ),
    ]
}
