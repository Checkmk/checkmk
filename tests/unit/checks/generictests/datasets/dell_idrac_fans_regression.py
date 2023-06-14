#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "dell_idrac_fans"


info = [
    ["1", "1", "", "System Board Fan1A", "", "", "", ""],
    ["2", "2", "", "System Board Fan1B", "", "", "", ""],
    ["3", "10", "", "System Board Fan2A", "", "", "", ""],
]


discovery = {"": [("3", {})]}


checks = {"": [("3", {}, [(2, "Status: FAILED, Name: System Board Fan2A", [])])]}
