#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "fortigate_memory"

info = [["42"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"levels": (30.0, 80.0)},
            [(1, "Usage: 42.00% (warn/crit at 30.00%/80.00%)", [("mem_usage", 42, 30.0, 80.0)])],
        ),
        (
            None,
            {"levels": (-80, -30)},
            [
                (3, "Absolute levels are not supported", []),
                (0, "Usage: 42.00%", [("mem_usage", 42, None, None, None, None)]),
            ],
        ),
    ],
}
