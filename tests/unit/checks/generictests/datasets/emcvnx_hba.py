#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "emcvnx_hba"


parsed = {
    "SP A Port 0": {"Blocks Read": 0, "Blocks Written": 0},
    "SP B Port 0": {},
    "SP B Port 3": {},
}


discovery = {"": [("SP A Port 0", None)]}


checks = {
    "": [
        (
            "SP A Port 0",
            {},
            [
                (
                    0,
                    "Read: 0 Blocks/s, Write: 0 Blocks/s",
                    [
                        ("read_blocks", 0, None, None, None, None),
                        ("write_blocks", 0, None, None, None, None),
                    ],
                )
            ],
        )
    ]
}
