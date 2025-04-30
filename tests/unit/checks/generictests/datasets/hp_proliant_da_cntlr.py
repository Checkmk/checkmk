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
    ['6', '1', '6', '2', '1', '8', '1', 'PEYHN0ARCC307J'],
]

discovery = {"": [("0", None), ("3", None), ("6", None)]}

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
        (
            "6",
            {},
            [
                (
                    1,
                    "Condition: ok, Board-Condition: other (The instrument agent does not recognize the status of the controller. You may need to upgrade the instrument agent.) (!), Board-Status: enabled, (Role: other, Model: 1, Slot: 6, Serial: PEYHN0ARCC307J)",
                    []
                )
            ]
        ),
    ]
}
