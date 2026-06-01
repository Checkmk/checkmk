#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.dell.agent_based.dell_idrac_power import (
    check_dell_idrac_power,
    check_dell_idrac_power_unit,
    discover_dell_idrac_power,
    discover_dell_idrac_power_unit,
    parse_dell_idrac_power,
)

# Section layout (see snmp_section_dell_idrac_power):
#   section[0]: power unit redundancy -> [index, status, count]
#   section[1]: power supply unit     -> [index, status, psu_type, location]
#   section[2]: firmware version      -> [[firmware_shortname]]
_REDUNDANCY = [["1", "1", "2"], ["2", "2", "2"]]
_POWER_UNITS = [
    ["1", "3", "9", "PS1 Status"],
    ["2", "5", "9", "PS2 Status"],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [Service(item="1"), Service(item="2")],
        ),
        (
            [[], _POWER_UNITS, []],
            [],
        ),
    ],
)
def test_discover_dell_idrac_power(
    string_table: Sequence[StringTable], expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for dell_idrac_power check."""
    parsed = parse_dell_idrac_power(string_table)
    result = list(discover_dell_idrac_power(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        pytest.param(
            "1",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [Result(state=State.OK, summary="Status: full")],
            id="v4 firmware: status 1 -> full (OK)",
        ),
        pytest.param(
            "2",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [Result(state=State.CRIT, summary="Status: lost")],
            id="v4 firmware: status 2 -> lost (CRIT)",
        ),
        pytest.param(
            "1",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC9"]]],
            [Result(state=State.UNKNOWN, summary="Status: other")],
            id="v3 firmware: status 1 -> other (UNKNOWN)",
        ),
        pytest.param(
            "2",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC9"]]],
            [Result(state=State.UNKNOWN, summary="Status: unknown")],
            id="v3 firmware: status 2 -> unknown (UNKNOWN)",
        ),
        pytest.param(
            "1",
            [_REDUNDANCY, _POWER_UNITS, []],
            [Result(state=State.OK, summary="Status: full")],
            id="missing firmware falls back to v4",
        ),
        pytest.param(
            "3",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [],
            id="unknown item yields no result",
        ),
    ],
)
def test_check_dell_idrac_power(
    item: str,
    string_table: Sequence[StringTable],
    expected_results: Sequence[Any],
) -> None:
    """Test check function for dell_idrac_power check."""
    parsed = parse_dell_idrac_power(string_table)
    result = list(check_dell_idrac_power(item, parsed))
    assert result == expected_results


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [Service(item="1"), Service(item="2")],
        ),
    ],
)
def test_discover_dell_idrac_power_unit(
    string_table: Sequence[StringTable], expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for dell_idrac_power_unit check."""
    parsed = parse_dell_idrac_power(string_table)
    result = list(discover_dell_idrac_power_unit(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        pytest.param(
            "1",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [Result(state=State.OK, summary="Status: OK, Type: AC, Name: PS1 Status")],
            id="status 3 (OK), type 9 (AC)",
        ),
        pytest.param(
            "2",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [Result(state=State.CRIT, summary="Status: CRITICAL, Type: AC, Name: PS2 Status")],
            id="status 5 (CRITICAL), type 9 (AC)",
        ),
        pytest.param(
            "3",
            [_REDUNDANCY, _POWER_UNITS, [["iDRAC10"]]],
            [],
            id="unknown item yields no result",
        ),
    ],
)
def test_check_dell_idrac_power_unit(
    item: str,
    string_table: Sequence[StringTable],
    expected_results: Sequence[Any],
) -> None:
    """Test check function for dell_idrac_power_unit check."""
    parsed = parse_dell_idrac_power(string_table)
    result = list(check_dell_idrac_power_unit(item, parsed))
    assert result == expected_results
