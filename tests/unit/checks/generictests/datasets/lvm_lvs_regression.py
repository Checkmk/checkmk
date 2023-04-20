#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "lvm_lvs"

info = [
    ["mysql", "VG-OL-data", "Vwi-aotz--", "31138512896", "tp", "", "77.75", "", "", "", "", ""],
    ["onkostar", "VG-OL-data", "Vwi-aotz--", "13958643712", "tp", "", "99.99", "", "", "", "", ""],
    ["tp", "VG-OL-data", "twi-aotz--", "53573844992", "", "", "71.25", "34.86", "", "", "", ""],
    ["root", "VG-OL-root", "-wi-ao----", "12884901888", "", "", "", "", "", "", "", ""],
    ["swap", "VG-OL-swap", "-wi-ao----", "8585740288", "", "", "", "", "", "", "", ""],
]

discovery = {"": [("VG-OL-data/tp", {})]}

checks = {
    "": [
        (
            "VG-OL-data/tp",
            {"levels_data": (80.0, 90.0), "levels_meta": (80.0, 90.0)},
            [
                (0, "Data usage: 71.25%", [("data_usage", 71.25, 80.0, 90.0, None, None)]),
                (0, "Meta usage: 34.86%", [("meta_usage", 34.86, 80.0, 90.0, None, None)]),
            ],
        )
    ]
}
