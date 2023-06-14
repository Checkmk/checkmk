#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "sansymphony_virtualdiskstatus"


info = [
    ["testvmfs01", "Online"],
    ["vmfs01", "anything", "else"],
]


discovery = {
    "": [
        ("testvmfs01", {}),
        ("vmfs01", {}),
    ],
}


checks = {
    "": [
        (
            "testvmfs01",
            {},
            [
                (0, "Volume state is: Online", []),
            ],
        ),
        (
            "vmfs01",
            {},
            [
                (2, "Volume state is: anything else", []),
            ],
        ),
    ],
}
