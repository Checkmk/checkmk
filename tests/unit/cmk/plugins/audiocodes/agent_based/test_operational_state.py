#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.audiocodes.agent_based.lib import parse_audiocodes_operational_state
from cmk.plugins.audiocodes.agent_based.module_names import (
    parse_module_names,
)
from cmk.plugins.audiocodes.agent_based.operational_state import (
    check_audiocodes_operational_state,
    discover_audiocodes_operational_state,
)

_STRING_TABLE_OPERATIONAL_STATE = [
    ["67387393", "2", "1", "6"],
    ["67907585", "2", "1", "2"],
]
_STRING_TABLE_MODULE_NAMES = [
    ["67387393", "Mediant-4000 Media Processing Module"],
    ["67641344", "Mediant-4000 Slot"],
    ["67903488", "Mediant-4000 Slot"],
    ["67907585", "Mediant-4000 CPU Module"],
]


def test_discovery_function() -> None:
    section_operational_state = parse_audiocodes_operational_state(_STRING_TABLE_OPERATIONAL_STATE)
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    assert list(
        discover_audiocodes_operational_state(section_module_names, section_operational_state)
    ) == [
        Service(item="Mediant-4000 Media Processing Module 67387393"),
        Service(item="Mediant-4000 CPU Module 67907585"),
    ]


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            "not_found",
            [],
            id="Item not found",
        ),
        pytest.param(
            "Mediant-4000 Media Processing Module 67387393",
            [
                Result(state=State.OK, summary="Operational state: Enabled"),
                Result(state=State.OK, notice="Presence: Module present"),
                Result(state=State.UNKNOWN, summary="HA status: Not applicable"),
            ],
            id="Not applicable HA Status",
        ),
        pytest.param(
            "Mediant-4000 CPU Module 67907585",
            [
                Result(state=State.OK, summary="Operational state: Enabled"),
                Result(state=State.OK, notice="Presence: Module present"),
                Result(state=State.OK, summary="HA status: Active"),
            ],
            id="Everything OK",
        ),
    ],
)
def test_check_function(
    item: str,
    expected: CheckResult,
) -> None:
    section_operational_state = parse_audiocodes_operational_state(_STRING_TABLE_OPERATIONAL_STATE)
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    assert (
        list(
            check_audiocodes_operational_state(
                item, section_module_names, section_operational_state
            )
        )
        == expected
    )
