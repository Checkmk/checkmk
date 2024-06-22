#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
from cmk.plugins.collection.agent_based.ucd_mem import parse_ucd_mem

checkname = "ucd_mem"

parsed = parse_ucd_mem([[["10", "9", "", "", "", "", "", "", "", "", "", ""]]])

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {
                "levels_ram": ("abs_free", (2048, 1024)),
            },
            [
                (
                    0,
                    "RAM: 10.00% - 1.00 KiB of 10.0 KiB",
                    [
                        ("mem_used", 1024, 8192.0, 9216.0, 0, 10240),
                        ("mem_used_percent", 10.0, 80.0, 90.0, 0.0, None),
                    ],
                ),
            ],
        )
    ]
}
