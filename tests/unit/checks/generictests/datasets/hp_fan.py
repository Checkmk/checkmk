#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "hp_fan"

info = [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]]

discovery = {"": [("2/0", None), ("3/1", None), ("4/2", None)]}

checks = {
    "": [
        ("2/0", {}, [(0, "ok", [])]),
        ("3/1", {}, [(1, "underspeed", [])]),
        ("4/2", {}, [(2, "removed", [])]),
    ]
}
