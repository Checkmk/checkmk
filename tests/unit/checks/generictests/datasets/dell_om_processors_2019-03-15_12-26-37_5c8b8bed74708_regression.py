#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "dell_om_processors"


info = [["1", "5", "Intel", "3", "129"], ["2", "3", "Intel", "3", "128"]]


discovery = {"": [("1", None), ("2", None)]}


checks = {
    "": [
        ("1", {}, [(3, "[Intel] CPU status: BIOS Disabled, CPU reading: unknown[129]", [])]),
        ("2", {}, [(0, "[Intel] CPU status: Enabled, CPU reading: Present", [])]),
    ]
}
