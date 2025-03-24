#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based.printer_supply import (
    check_printer_supply,
    CheckParams,
    discovery_printer_supply,
    parse_printer_supply,
    PrinterSupply,
    Section,
    SupplyClass,
    Unit,
)

DEFAULT_PARAMETERS = CheckParams(
    levels=(20.0, 10.0),
    upturn_toner=False,
    some_remaining_ink=State.WARN.value,
    some_remaining_space=State.WARN.value,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                [["1.1", "black\x00"]],
                [
                    [
                        "Patrone Schwarz 508A HP CF360A\x00",
                        "19",
                        "100",
                        "9",
                        SupplyClass.CONTAINER,
                        "1",
                    ]
                ],
            ],
            {
                "Patrone Schwarz 508A HP CF360A": PrinterSupply(
                    Unit("%"), 100, 9, SupplyClass.CONTAINER, "black"
                ),
            },
            id="with null bytes",
        ),
    ],
)
def test_parse_printer_supply(
    string_table: Sequence[StringTable], expected_result: Section
) -> None:
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
def test_inventory_printer_supply(
    info: Sequence[StringTable], expected_result: DiscoveryResult
) -> None:
    section = parse_printer_supply(info)
    result = discovery_printer_supply(section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, info, expected_result",
    [
        (
            "Black Ink Cartridge",
            {**DEFAULT_PARAMETERS, "some_remaining_ink": 3},
            [
                [["1.4", "black"]],
                [["Black Ink Cartridge", "15", "-2", "-3", "3", "4"]],
            ],
            [
                Result(state=State.UNKNOWN, summary="Some ink remaining"),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
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
            DEFAULT_PARAMETERS,
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
            DEFAULT_PARAMETERS,
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
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "-2", "5", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply: 5 tenths of milliliters"),
                Metric("supply_toner_magenta", 5),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "0", "5", "3", "1"],
                ],
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Supply level remaining: 5.00% (warn/crit below 20.00%/10.00%)",
                ),
                Metric("supply_toner_magenta", 5.0),
                Result(state=State.OK, summary="Supply: 5 of max. 100 tenths of milliliters"),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "0", "15", "3", "1"],
                ],
            ],
            [
                Result(
                    state=State.WARN,
                    summary="Supply level remaining: 15.00% (warn/crit below 20.00%/10.00%)",
                ),
                Metric("supply_toner_magenta", 15.0),
                Result(state=State.OK, summary="Supply: 15 of max. 100 tenths of milliliters"),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "15", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 25.00%"),
                Metric("supply_toner_magenta", 25.0),
                Result(state=State.OK, summary="Supply: 25 of max. 100 tenths of milliliters"),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "4", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 25.00%"),
                Metric("supply_toner_magenta", 25.0),
                Result(state=State.OK, summary="Supply: 25 of max. 100 micrometers"),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "1", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 25.00%"),
                Metric("supply_toner_magenta", 25.0),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 25.00%"),
                Metric("supply_toner_magenta", 25.0),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
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
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"], ["1.4", "black"]],
                [
                    ["Black Ink Cartridge", "19", "0", "25", "3", "1"],
                    ["Toner Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 25.00%"),
                Metric("supply_toner_magenta", 25.0),
            ],
        ),
        (
            "Toner Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"], ["1.2", "black"]],
                [
                    ["Toner Cartridge", "19", "0", "25", "3", ""],
                    ["Black Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 25.00%"),
                Metric("supply_toner_other", 25.0),
            ],
        ),
        (
            "Magenta Toner Cartridge2",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"], ["1.2", "black"]],
                [
                    ["Toner Cartridge1", "19", "0", "25", "3", "1"],
                    ["Toner Cartridge2", "19", "0", "25", "3", ""],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 25.00%"),
                Metric("supply_toner_magenta", 25.0),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            {**DEFAULT_PARAMETERS, "upturn_toner": True},
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "3", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 75.00%"),
                Metric("supply_toner_magenta", 75.0),
            ],
        ),
        (
            "Magenta Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Magenta Ink Cartridge", "19", "0", "25", "4", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 75.00%"),
                Metric("supply_toner_magenta", 75.0),
            ],
        ),
        (
            "Ink Cartridge",
            DEFAULT_PARAMETERS,
            [
                [["1.1", "magenta"]],
                [
                    ["Ink Cartridge", "19", "0", "25", "4", "1"],
                ],
            ],
            [
                Result(state=State.OK, summary="Supply level remaining: 75.00%"),
                Metric("supply_toner_magenta", 75.0),
            ],
        ),
    ],
)
def test_check_printer_supply(
    item: str,
    params: CheckParams,
    info: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    section = parse_printer_supply(info)
    result = check_printer_supply(item, params, section)
    assert list(result) == expected_result


def _get_section_with_color_in_description(item: str) -> Section:
    max_capacity, supply_level, container_class = "0", "25", str(SupplyClass.CONTAINER)
    info = [[["1.1", ""]], [[item, "", max_capacity, supply_level, container_class, ""]]]
    return parse_printer_supply(info)


@pytest.mark.parametrize("item", ["Black", "Schwarz", "Noir", "Negra"])
def test_check_printer_supply_black_translations(item: str) -> None:
    section = _get_section_with_color_in_description(item)

    _, value = list(check_printer_supply(item, DEFAULT_PARAMETERS, section))
    expected = Metric("supply_toner_black", 25.0)

    assert value == expected


@pytest.mark.parametrize("item", ["Cyan", "Zyan", "Cian"])
def test_check_printer_supply_cyan_translations(item: str) -> None:
    section = _get_section_with_color_in_description(item)

    _, value = list(check_printer_supply(item, DEFAULT_PARAMETERS, section))
    expected = Metric("supply_toner_cyan", 25.0)

    assert value == expected


@pytest.mark.parametrize("item", ["Yellow", "Gelb", "Jaune", "Amarilla"])
def test_check_printer_supply_yellow_translations(item: str) -> None:
    section = _get_section_with_color_in_description(item)

    _, value = list(check_printer_supply(item, DEFAULT_PARAMETERS, section))
    expected = Metric("supply_toner_yellow", 25.0)

    assert value == expected
