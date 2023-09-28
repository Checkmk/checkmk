#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "teracom_tcw241_digital"


info = [
    [["Tank_Status", "NEA_Status", "Digital Input 3", "Digital Input 4"]],
    [["1", "1", "1", "1"]],
]


discovery = {"": [("4", {}), ("3", {}), ("2", {}), ("1", {})]}


checks = {
    "": [
        ("4", {}, [(0, "[Digital Input 4] is open", [])]),
        ("3", {}, [(0, "[Digital Input 3] is open", [])]),
        ("2", {}, [(0, "[NEA_Status] is open", [])]),
        ("1", {}, [(0, "[Tank_Status] is open", [])]),
    ]
}
