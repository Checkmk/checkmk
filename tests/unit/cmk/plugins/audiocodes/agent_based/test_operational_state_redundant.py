#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State
from cmk.plugins.audiocodes.agent_based.lib import parse_audiocodes_operational_state
from cmk.plugins.audiocodes.agent_based.operational_state_redundant import (
    check_audiocodes_operational_state_redundant,
    discover_audiocodes_operational_state_redundant,
)

_STRING_TABLE_OPERATIONAL_STATE_REDUNDANT = [
    ["1", "2", "1", "6"],
    ["3", "2", "1", "3"],
]


def test_discovery_function() -> None:
    section_operational_state_redundant = parse_audiocodes_operational_state(
        _STRING_TABLE_OPERATIONAL_STATE_REDUNDANT
    )
    assert section_operational_state_redundant is not None
    assert list(
        discover_audiocodes_operational_state_redundant(section_operational_state_redundant)
    ) == [
        Service(item="1"),
        Service(item="3"),
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
            "1",
            [
                Result(state=State.OK, summary="Operational state: Enabled"),
                Result(state=State.OK, notice="Presence: Module present"),
                Result(state=State.UNKNOWN, summary="HA status: Not applicable"),
            ],
            id="Not applicable HA Status",
        ),
        pytest.param(
            "3",
            [
                Result(state=State.OK, summary="Operational state: Enabled"),
                Result(state=State.OK, notice="Presence: Module present"),
                Result(state=State.OK, summary="HA status: Redundant"),
            ],
            id="Everything OK",
        ),
    ],
)
def test_check_function(
    item: str,
    expected: CheckResult,
) -> None:
    section_operational_state_redundant = parse_audiocodes_operational_state(
        _STRING_TABLE_OPERATIONAL_STATE_REDUNDANT
    )
    assert section_operational_state_redundant is not None
    assert (
        list(
            check_audiocodes_operational_state_redundant(item, section_operational_state_redundant)
        )
        == expected
    )
