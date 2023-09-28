#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "db2_logsizes"

info = [
    ["[[[db2mpss:ASMPROD]]]"],
    ["TIMESTAMP", "1474466290"],
    ["usedspace", "2204620"],
    ["logfilsiz", "2000"],
    ["logprimary", "5"],
    ["logsecond", "20"],
]

discovery = {"": [("db2mpss:ASMPROD", {})]}

checks = {
    "": [
        (
            "db2mpss:ASMPROD",
            {"levels": (-20.0, -10.0)},
            [
                (
                    0,
                    "Used: 1.03% - 2.00 MiB of 195 MiB",
                    [
                        ("fs_used", 2, 156.0, 175.0, 0, 195.0),
                        ("fs_free", 193, None, None, 0, None),
                        ("fs_used_percent", 1.0256410256410255, 80.0, 90.0, 0.0, 100.0),
                        ("fs_size", 195, None, None, 0, None),
                    ],
                )
            ],
        )
    ]
}
