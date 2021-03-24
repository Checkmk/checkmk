#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("info, expected_result", [([
    [["1.4", "black"]],
    [["Black Ink Cartridge", "15", "-2", "-3", "3", "4"]],
], [("Black Ink Cartridge", {})])])
def test_inventory_printer_supply(info, expected_result):
    section = Check("printer_supply").run_parse(info)
    result = Check("printer_supply").run_discovery(section)
    assert result == expected_result


@pytest.mark.parametrize("item, params, info, expected_result", [
    ("Black Ink Cartridge", {
        "levels": (20.0, 10.0)
    }, [
        [["1.4", "black"]],
        [["Black Ink Cartridge", "15", "-2", "-3", "3", "4"]],
    ], (1, "Some remaining", [("pages", -3, -0.4, -0.2, 0, -2)])),
    ("Magenta Ink Cartridge", {
        "levels": (20.0, 10.0)
    }, [
        [["1.1", "magenta"]],
        [
            ["Magenta Ink Cartridge", "15", "-2", "-1", "3", "1"],
        ],
    ], (0, "There are no restrictions on this supply")),
    ("Magenta Ink Cartridge", {
        "levels": (20.0, 10.0)
    }, [
        [["1.1", "magenta"]],
        [
            ["Magenta Ink Cartridge", "15", "-2", "-2", "3", "1"],
        ],
    ], None),
    ("Magenta Ink Cartridge", {
        "levels": (20.0, 10.0)
    }, [
        [["1.1", "magenta"]],
        [
            ["Magenta Ink Cartridge", "15", "-3", "-2", "3", "1"],
        ],
    ], (3, " Unknown level")),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "15", "-2", "5", "3", "1"],
            ],
        ],
        (0, "Level: 5", [("pages", 5)]),
    ),
    ("Magenta Ink Cartridge", {
        "levels": (20.0, 10.0)
    }, [
        [["1.1", "magenta"]],
        [
            ["Magenta Ink Cartridge", "15", "0", "5", "3", "1"],
        ],
    ], (2, "Remaining: 5% (warn/crit at 20%/10%), Supply: 5 of max. 100 tenths of milliliters", [
        ("pages", 5, 20.0, 10.0, 0, 100)
    ])),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "15", "0", "15", "3", "1"],
            ],
        ],
        (1, "Remaining: 15% (warn/crit at 20%/10%), Supply: 15 of max. 100 tenths of milliliters", [
            ("pages", 15, 20.0, 10.0, 0, 100)
        ]),
    ),
    (
        "Magenta Ink Cartridge",
        (20.0, 10.0),
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "15", "0", "15", "3", "1"],
            ],
        ],
        (1, "Remaining: 15% (warn/crit at 20%/10%), Supply: 15 of max. 100 tenths of milliliters", [
            ("pages", 15, 20.0, 10.0, 0, 100)
        ]),
    ),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "15", "0", "25", "3", "1"],
            ],
        ],
        (0, "Remaining: 25%, Supply: 25 of max. 100 tenths of milliliters", [
            ("pages", 25, 20.0, 10.0, 0, 100)
        ]),
    ),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "4", "0", "25", "3", "1"],
            ],
        ],
        (0, "Remaining: 25%, Supply: 25 of max. 100 micrometers", [("pages", 25, 20.0, 10.0, 0, 100)
                                                                  ]),
    ),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "1", "0", "25", "3", "1"],
            ],
        ],
        (0, "Remaining: 25%, Supply: 25 of max. 100", [("pages", 25, 20.0, 10.0, 0, 100)]),
    ),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
            ],
        ],
        (0, "Remaining: 25%, Supply: 25 of max. 100%", [("pages", 25, 20.0, 10.0, 0, 100)]),
    ),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [
                ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
            ],
        ],
        None,
    ),
    (
        "Magenta Ink Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "19", "max_capacity", "25", "3", "1"],
            ],
        ],
        None,
    ),
    (
        "Magenta Toner Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"], ["1.4", "black"]],
            [
                ["Black Ink Cartridge", "19", "0", "25", "3", "1"],
                ["Toner Cartridge", "19", "0", "25", "3", "1"],
            ],
        ],
        (0, "Remaining: 25%, Supply: 25 of max. 100%", [("pages", 25, 20.0, 10.0, 0, 100)]),
    ),
    (
        "Toner Cartridge",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"], ["1.2", "black"]],
            [
                ["Toner Cartridge", "19", "0", "25", "3", ""],
                ["Black Ink Cartridge", "19", "0", "25", "3", "1"],
            ],
        ],
        (0, "Remaining: 25%, Supply: 25 of max. 100%", [("pages", 25, 20.0, 10.0, 0, 100)]),
    ),
    (
        "Magenta Toner Cartridge2",
        {
            "levels": (20.0, 10.0)
        },
        [
            [["1.1", "magenta"], ["1.2", "black"]],
            [
                ["Toner Cartridge1", "19", "0", "25", "3", "1"],
                ["Toner Cartridge2", "19", "0", "25", "3", ""],
            ],
        ],
        (0, "Remaining: 25%, Supply: 25 of max. 100%", [("pages", 25, 20.0, 10.0, 0, 100)]),
    ),
    (
        "Magenta Ink Cartridge",
        (20.0, 10.0, True),
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
            ],
        ],
        (0, "Remaining: 75%, Supply: 25 of max. 100%", [("pages", 25, 20.0, 10.0, 0, 100)]),
    ),
    (
        "Magenta Ink Cartridge",
        (20.0, 10.0),
        [
            [["1.1", "magenta"]],
            [
                ["Magenta Ink Cartridge", "19", "0", "25", "4", "1"],
            ],
        ],
        (0, "Remaining: 75%, Supply: 25 of max. 100%", [("pages", 25, 20.0, 10.0, 0, 100)]),
    ),
    (
        "Ink Cartridge",
        (20.0, 10.0),
        [
            [["1.1", "magenta"]],
            [
                ["Ink Cartridge", "19", "0", "25", "4", "1"],
            ],
        ],
        (0, "[magenta] Remaining: 75%, Supply: 25 of max. 100%", [("pages", 25, 20.0, 10.0, 0, 100)
                                                                 ]),
    ),
])
def test_check_printer_supply(item, params, info, expected_result):
    section = Check("printer_supply").run_parse(info)
    result = Check("printer_supply").run_check(item, params, section)
    assert result == expected_result