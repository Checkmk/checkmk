#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.gude.agent_based.gude_relayport import (
    check_gude_relayport,
    discover_gude_relayport,
    parse_gude_relayport,
)

_STRING_TABLE = [
    ["TWTA 2", "1", "0", "0", "228", "4995", "0"],
    ["TWTA 3", "1", "0", "0", "190", "6000", "2"],
    ["TWTA 4", "0", "", "", "", "", ""],
]

_TABLE_INPUT: StringTable = [
    ["Power Port A1", "0", "", "", "", "", ""],
    ["Power Port A2", "0", "", "", "", "", ""],
    ["Power Port A3", "0", "", "", "", "", ""],
    ["Power Port A4", "0", "", "", "", "", ""],
    ["Power Port A5", "0", "", "", "", "", ""],
    ["Power Port A6", "0", "", "", "", "", ""],
    ["Power Port B1", "0", "", "", "", "", ""],
    ["Power Port B2", "0", "", "", "", "", ""],
    ["Power Port B3", "0", "", "", "", "", ""],
    ["Power Port B4", "0", "", "", "", "", ""],
    ["Power Port B5", "0", "", "", "", "", ""],
    ["Power Port B6", "0", "", "", "", "", ""],
]


def test_discovery_function() -> None:
    assert list(discover_gude_relayport(parse_gude_relayport(_STRING_TABLE))) == [
        Service(item="TWTA 2"),
        Service(item="TWTA 3"),
        Service(item="TWTA 4"),
    ]


@pytest.mark.parametrize(
    "item, params, expected",
    [
        pytest.param(
            "not_found",
            {
                "voltage": (220, 210),
                "current": (15, 16),
            },
            [],
            id="Item not found",
        ),
        pytest.param(
            "TWTA 2",
            {
                "voltage": (220, 210),
                "current": (15, 16),
            },
            [
                Result(state=State.OK, summary="Device status: on(0)"),
                Result(state=State.OK, summary="Voltage: 228.0 V"),
                Metric("voltage", 228.0),
                Result(state=State.OK, summary="Current: 0.0 A"),
                Metric("current", 0.0, levels=(15.0, 16.0)),
                Result(state=State.OK, summary="Power: 0.0 W"),
                Metric("power", 0.0),
                Result(state=State.OK, summary="Apparent Power: 0.0 VA"),
                Metric("appower", 0.0),
                Result(state=State.OK, summary="Frequency: 50.0 Hz"),
                Metric("frequency", 49.95),
            ],
            id="Everything is OK",
        ),
        pytest.param(
            "TWTA 3",
            {
                "voltage": (220, 210),
                "current": (15, 16),
            },
            [
                Result(state=State.OK, summary="Device status: on(0)"),
                Result(
                    state=State.CRIT, summary="Voltage: 190.0 V (warn/crit below 220.0 V/210.0 V)"
                ),
                Metric("voltage", 190.0),
                Result(state=State.OK, summary="Current: 0.0 A"),
                Metric("current", 0.0, levels=(15.0, 16.0)),
                Result(state=State.OK, summary="Power: 0.0 W"),
                Metric("power", 0.0),
                Result(state=State.OK, summary="Apparent Power: 2.0 VA"),
                Metric("appower", 2.0),
                Result(state=State.OK, summary="Frequency: 60.0 Hz"),
                Metric("frequency", 60.0),
            ],
            id="Voltage too low. CRIT State",
        ),
        pytest.param(
            "TWTA 4",
            {
                "voltage": (220, 210),
                "current": (15, 16),
            },
            [Result(state=State.CRIT, summary="Device status: off(2)")],
            id="Voltage too low",
        ),
    ],
)
def test_check_function(
    item: str,
    params: Mapping[str, Any],
    expected: CheckResult,
) -> None:
    assert list(check_gude_relayport(item, params, parse_gude_relayport(_STRING_TABLE))) == expected


def test_not_having_data_does_not_crash_parsing() -> None:
    parsed_section = parse_gude_relayport(_TABLE_INPUT)
    assert parsed_section
    result = list(check_gude_relayport("Power Port A2", {}, parsed_section))
    assert result == [Result(state=State.CRIT, summary="Device status: off(2)")]
