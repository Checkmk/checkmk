#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from copy import deepcopy

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.audiocodes.agent_based.leds import (
    check_audiocodes_leds,
    discover_audiocodes_leds,
    parse_audiocodes_leds,
)
from cmk.plugins.audiocodes.agent_based.module_names import (
    parse_module_names,
)

_STRING_TABLE_LEDS_ALL_GREEN = [
    [
        ["67387393", "âîîîîîîîîîîîîîîîîîîî"],
        ["67907585", "âîîîîîîîîîîîîîîîîîîî"],
    ],
    [
        ["1", "âîîîîîîîîîîîîîîîîîîî", "M4K's Fan-Tray ID 1"],
        ["2", "âîîîîîîîîîîîîîîîîîîî", "M4K's Fan-Tray ID 2"],
    ],
    [
        ["1", "âîîîîîîîîîîîîîîîîîîî"],
        ["2", "âîîîîîîîîîîîîîîîîîîî"],
    ],
    [
        ["1", "âîîîîîîîîîîîîîîîîîîî", "M4K's Fan-Tray ID 1"],
        ["2", "âîîîîîîîîîîîîîîîîîîî", "M4K's Fan-Tray ID 2"],
    ],
    [
        ["1", "âîîîîîîîîîîîîîîîîîîî"],
        ["2", "âîîîîîîîîîîîîîîîîîîî"],
    ],
]

_STRING_TABLE_LEDS_BLUE = deepcopy(_STRING_TABLE_LEDS_ALL_GREEN)
_STRING_TABLE_LEDS_BLUE[0][1][1] = "ëîîîîîîîîîîîîîîîîîîî"

_STRING_TABLE_LEDS_ONE_RED = deepcopy(_STRING_TABLE_LEDS_ALL_GREEN)
_STRING_TABLE_LEDS_ONE_RED[0][1][1] = "äîîîîîîîîîîîîîîîîîîî"

_STRING_TABLE_LEDS_ONE_RED_ONE_YELLOW = deepcopy(_STRING_TABLE_LEDS_ALL_GREEN)
_STRING_TABLE_LEDS_ONE_RED_ONE_YELLOW[0][1][1] = "äîîîîîîîîîîîîîîîîîîî"
_STRING_TABLE_LEDS_ONE_RED_ONE_YELLOW[3][1][1] = "æîîîîîîîîîîîîîîîîîîî"

_STRING_TABLE_MODULE_NAMES = [
    ["67387393", "Mediant-4000 Media Processing Module"],
    ["67907585", "Mediant-4000 CPU Module"],
]


def test_discovery_function() -> None:
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    section_leds = parse_audiocodes_leds(_STRING_TABLE_LEDS_ALL_GREEN)
    assert list(discover_audiocodes_leds(section_module_names, section_leds)) == [
        Service(),
    ]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            _STRING_TABLE_LEDS_ALL_GREEN,
            [
                Result(state=State.OK, notice="Mediant-4000 Media Processing Module LED: on-green"),
                Result(state=State.OK, notice="Mediant-4000 CPU Module LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 2 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 (redundant) LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 2 (redundant) LED: on-green"),
                Result(state=State.OK, notice="Power supply 1 LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 LED: on-green"),
                Result(state=State.OK, notice="Power supply 1 (redundant) LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 (redundant) LED: on-green"),
                Result(state=State.OK, summary="10 green LEDs"),
            ],
            id="all LEDs green",
        ),
        pytest.param(
            _STRING_TABLE_LEDS_BLUE,
            [
                Result(state=State.OK, notice="Mediant-4000 Media Processing Module LED: on-green"),
                Result(state=State.WARN, notice="Mediant-4000 CPU Module LED: flashing-blue"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 2 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 (redundant) LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 2 (redundant) LED: on-green"),
                Result(state=State.OK, notice="Power supply 1 LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 LED: on-green"),
                Result(state=State.OK, notice="Power supply 1 (redundant) LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 (redundant) LED: on-green"),
                Result(state=State.OK, summary="9 green LEDs"),
                Result(state=State.OK, summary="1 blue LED"),
            ],
            id="one blue LED (warning)",
        ),
        pytest.param(
            _STRING_TABLE_LEDS_ONE_RED,
            [
                Result(state=State.OK, notice="Mediant-4000 Media Processing Module LED: on-green"),
                Result(state=State.CRIT, notice="Mediant-4000 CPU Module LED: on-red"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 2 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 (redundant) LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 2 (redundant) LED: on-green"),
                Result(state=State.OK, notice="Power supply 1 LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 LED: on-green"),
                Result(state=State.OK, notice="Power supply 1 (redundant) LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 (redundant) LED: on-green"),
                Result(state=State.OK, summary="9 green LEDs"),
                Result(state=State.OK, summary="1 red LED"),
            ],
            id="one red LED",
        ),
        pytest.param(
            _STRING_TABLE_LEDS_ONE_RED_ONE_YELLOW,
            [
                Result(state=State.OK, notice="Mediant-4000 Media Processing Module LED: on-green"),
                Result(state=State.CRIT, notice="Mediant-4000 CPU Module LED: on-red"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 2 LED: on-green"),
                Result(state=State.OK, notice="M4K's Fan-Tray ID 1 (redundant) LED: on-green"),
                Result(state=State.WARN, notice="M4K's Fan-Tray ID 2 (redundant) LED: on-yellow"),
                Result(state=State.OK, notice="Power supply 1 LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 LED: on-green"),
                Result(state=State.OK, notice="Power supply 1 (redundant) LED: on-green"),
                Result(state=State.OK, notice="Power supply 2 (redundant) LED: on-green"),
                Result(state=State.OK, summary="8 green LEDs"),
                Result(state=State.OK, summary="1 red LED"),
                Result(state=State.OK, summary="1 yellow LED"),
            ],
            id="one red LED",
        ),
    ],
)
def test_check_function(
    string_table: Sequence[StringTable],
    expected: CheckResult,
) -> None:
    section_fru = parse_audiocodes_leds(string_table)
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    assert list(check_audiocodes_leds(section_module_names, section_fru)) == expected
