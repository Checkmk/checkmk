#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "hp_proliant_da_cntlr"

info = [
    ["0", "54", "0", "2", "1", "2", "2", "N/A"],
    ["3", "52", "3", "3", "1", "2", "2", "PXXXX0BRH6X59X"],
]

discovery = {"": [("0", None), ("3", None)]}

checks = {
    "": [
        (
            "0",
            {},
            [
                (
                    0,
                    "Condition: ok, Board-Condition: ok, Board-Status: ok, (Role: other, Model: 54, Slot: 0, Serial: N/A)",
                    [],
                )
            ],
        ),
        (
            "3",
            {},
            [
                (
                    1,
                    "Condition: degraded (!), Board-Condition: ok, Board-Status: ok, (Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X)",
                    [],
                )
            ],
        ),
    ]
}
