#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "hwg_temp"

info = [["1", "Netzwerk-Rack", "1", "23.8", "1"], ["2", "Library-Rack", "1", "23.0", "1"]]

discovery = {"": [("1", {}), ("2", {})]}

checks = {
    "": [
        (
            "1",
            {"levels": (30, 35)},
            [
                (
                    0,
                    "23.8 °C (Description: Netzwerk-Rack, Status: normal)",
                    [("temp", 23.8, 30.0, 35.0, None, None)],
                )
            ],
        ),
        (
            "2",
            {"levels": (30, 35)},
            [
                (
                    0,
                    "23.0 °C (Description: Library-Rack, Status: normal)",
                    [("temp", 23.0, 30.0, 35.0, None, None)],
                )
            ],
        ),
    ]
}
