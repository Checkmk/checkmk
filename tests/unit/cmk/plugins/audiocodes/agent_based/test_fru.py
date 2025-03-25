#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.audiocodes.agent_based.fru import (
    check_audiocodes_fru,
    discover_audiocodes_fru,
    parse_audiocodes_fru,
)
from cmk.plugins.audiocodes.agent_based.module_names import (
    parse_module_names,
)

_STRING_TABLE_FRU = [
    ["67387393", "4", "7"],
    ["67907585", "4", "7"],
]

_STRING_TABLE_MODULE_NAMES = [
    ["67387393", "Mediant-4000 Media Processing Module"],
    ["67641344", "Mediant-4000 Slot"],
    ["67903488", "Mediant-4000 Slot"],
    ["67907585", "Mediant-4000 CPU Module"],
]


def test_discovery_function() -> None:
    section_fru = parse_audiocodes_fru(_STRING_TABLE_FRU)
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    assert list(discover_audiocodes_fru(section_module_names, section_fru)) == [
        Service(item="Mediant-4000 Media Processing Module 67387393"),
        Service(item="Mediant-4000 CPU Module 67907585"),
    ]


@pytest.mark.parametrize(
    "item, string_table, expected",
    [
        pytest.param(
            "not_found",
            _STRING_TABLE_FRU,
            [],
            id="Item not found",
        ),
        pytest.param(
            "Mediant-4000 CPU Module 67907585",
            _STRING_TABLE_FRU,
            [
                Result(state=State.UNKNOWN, summary="Action: Not applicable"),
                Result(state=State.UNKNOWN, summary="Status: Not applicable"),
            ],
            id="Everything is UNKNOWN",
        ),
        pytest.param(
            "Mediant-4000 Media Processing Module 67387393",
            [
                ["67387393", "1", "2"],
                ["67907585", "4", "7"],
            ],
            [
                Result(state=State.OK, summary="Action: Action done"),
                Result(state=State.OK, summary="Status: Module exists and ok"),
            ],
            id="Everything is OK",
        ),
        pytest.param(
            "Mediant-4000 CPU Module 67907585",
            [
                ["67387393", "1", "2"],
                ["67907585", "2", "5"],
            ],
            [
                Result(state=State.WARN, summary="Action: Out of service"),
                Result(state=State.CRIT, summary="Status: Module mismatch"),
            ],
            id="Everything is WARN/CRIT",
        ),
    ],
)
def test_check_function(
    item: str,
    string_table: StringTable,
    expected: CheckResult,
) -> None:
    section_fru = parse_audiocodes_fru(string_table)
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    assert list(check_audiocodes_fru(item, section_module_names, section_fru)) == expected
