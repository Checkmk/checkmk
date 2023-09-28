#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "hp_psu"

info = [["1", "3", "25"], ["2", "3", "23"]]

discovery = {"": [("1", None), ("2", None)], "temp": [("1", {}), ("2", {})]}

checks = {
    "": [("1", {}, [(0, "Powered", [])]), ("2", {}, [(0, "Powered", [])])],
    "temp": [
        ("1", {"levels": (70, 80)}, [(0, "25 \xb0C", [("temp", 25, 70, 80, None, None)])]),
        ("2", {"levels": (70, 80)}, [(0, "23 \xb0C", [("temp", 23, 70, 80, None, None)])]),
    ],
}
