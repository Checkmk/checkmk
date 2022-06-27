#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.printer_supply import (
    check_printer_supply,
    discovery_printer_supply,
    parse_printer_supply,
    PrinterSupply,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                [["1.1", "black\x00"]],
                [["Patrone Schwarz 508A HP CF360A\x00", "19", "100", "9", "3", "1"]],
            ],
            {
                "Patrone Schwarz 508A HP CF360A": PrinterSupply("%", 100, 9, "3", "black"),
            },
            id="with null bytes",
        ),
    ],
)
def test_parse_printer_supply(string_table, expected_result) -> None:
    assert parse_printer_supply(string_table) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                [["1.4", "black"]],
                [["Black Ink Cartridge", "15", "-2", "-3", "3", "4"]],
            ],
            [Service(item="Black Ink Cartridge")],
        )
    ],
)
def test_inventory_printer_supply(info, expected_result) -> None:
    section = parse_printer_supply(info)
    result = discovery_printer_supply(section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, info, expected_result",
    [
        (
            "Black Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.4", "black"]],
                [["Black Ink Cartridge", "15", "-2", "-3", "3", "4"]],
            ],
            [
                Result(state=State.WARN, summary="Some remaining"),
                Metric("pages", -3, levels=(-0.4, -0.2), boundaries=(0, -2)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {
                "levels": (20.0, 10.0),
                "upturn_toner": False,
                "some_remaining": 1,
            },
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "-2", "-1", "3", "1"],
                ],
            ],
            [Result(state=State.OK, summary="There are no restrictions on this supply")],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "-2", "-2", "3", "1"],
                ],
            ],
            [],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "-3", "-2", "3", "1"],
                ],
            ],
            [Result(state=State.UNKNOWN, summary=" Unknown level")],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "-2", "5", "3", "1"],
                ],
            ],
            [Result(state=State.OK, summary="Level: 5"), Metric("pages", 5)],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "0", "5", "3", "1"],
                ],
            ],
            [
                Result(
                    state=State.CRIT, summary="Remaining: 5.00% (warn/crit below 20.00%/10.00%)"
                ),
                Result(state=State.OK, summary="Supply: 5 of max. 100 tenths of milliliters"),
                Metric("pages", 5, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "0", "15", "3", "1"],
                ],
            ],
            [
                Result(
                    state=State.WARN, summary="Remaining: 15.00% (warn/crit below 20.00%/10.00%)"
                ),
                Result(state=State.OK, summary="Supply: 15 of max. 100 tenths of milliliters"),
                Metric("pages", 15, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 25.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100 tenths of milliliters"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "4", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 25.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100 micrometers"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "1", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 25.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 25.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100%"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "19", "max_capacity", "25", "3", "1"],
                ],
            ],
            [],
        ),
        (
            "Magenta Toner Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"], ["1.4", "black"]],
                [
                    ["Black Ink Cartridge", "19", "0", "25", "3", "1"],
                    ["Toner Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 25.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100%"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Toner Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"], ["1.2", "black"]],
                [
                    ["Toner Cartridge", "19", "0", "25", "3", ""],
                    ["Black Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 25.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100%"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Toner Cartridge2",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"], ["1.2", "black"]],
                [
                    ["Toner Cartridge1", "19", "0", "25", "3", "1"],
                    ["Toner Cartridge2", "19", "0", "25", "3", ""],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 25.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100%"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": True, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 75.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100%"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "4", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Remaining: 75.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100%"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
        (
            "Ink Cartridge",
            {"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
            [
                [["1.1", "magenta"]],
                [
                    ["Ink Cartridge", "19", "0", "25", "4", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="[magenta] Remaining: 75.00%"),
                Result(state=State.OK, summary="Supply: 25 of max. 100%"),
                Metric("pages", 25, levels=(20.0, 10.0), boundaries=(0, 100)),
            ],
        ),
    ],
)
def test_check_printer_supply(item, params, info, expected_result) -> None:
    section = parse_printer_supply(info)
    result = check_printer_supply(item, params, section)
    assert list(result) == expected_result
