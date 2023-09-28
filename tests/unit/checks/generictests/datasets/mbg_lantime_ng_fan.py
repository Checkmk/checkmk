#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "mbg_lantime_ng_fan"

info = [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]]

discovery = {"": [("1", {}), ("2", {}), ("4", {}), ("5", {})]}

checks = {
    "": [
        ("1", {}, [(0, "Status: on", []), (0, "Errors: no", [])]),
        ("2", {}, [(0, "Status: on", []), (0, "Errors: no", [])]),
        ("4", {}, [(0, "Status: on", []), (0, "Errors: no", [])]),
        ("5", {}, [(0, "Status: on", []), (3, "Errors: not available", [])]),
    ]
}
