#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "win_printers"


info = [
    ["PrinterStockholm", "3", "4", "0"],
    ["Printer", "Berlin", "3", "4", "0"],
    ["WH1_BC_O3_UPS", "0", "3", "8"],
    [
        '"printerstatus","detectederrorstate"',
        "-Type",
        "OnlyIfInBoth",
        "|",
        "format-table",
        "-HideTableHeaders",
    ],
]


discovery = {"": [("PrinterStockholm", {}), ("Printer Berlin", {}), ("WH1_BC_O3_UPS", {})]}


checks = {
    "": [
        (
            "PrinterStockholm",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            [
                (0, "Current jobs: 3", []),
                (0, "State: Printing", []),
            ],
        ),
        (
            "Printer Berlin",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            [
                (0, "Current jobs: 3", []),
                (0, "State: Printing", []),
            ],
        ),
        (
            "WH1_BC_O3_UPS",
            {"crit_states": [9, 10], "warn_states": [8, 11]},
            [
                (0, "Current jobs: 0", []),
                (0, "State: Idle", []),
                (1, "Error state: Jammed", []),
            ],
        ),
    ]
}
