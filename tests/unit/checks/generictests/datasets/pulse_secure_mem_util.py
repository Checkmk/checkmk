#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "pulse_secure_mem_util"

info = [["8", "0"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"mem_used_percent": (90, 95), "swap_used_percent": (5, None)},
            [
                (0, "RAM used: 8.00%", [("mem_used_percent", 8, 90.0, 95.0, None, None)]),
                (0, "Swap used: 0%", [("swap_used_percent", 0, 5.0, None, None, None)]),
            ],
        )
    ]
}
