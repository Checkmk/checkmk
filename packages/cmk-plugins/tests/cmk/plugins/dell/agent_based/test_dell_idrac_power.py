#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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
#   section[2]: racInfoGroup scalars  -> [[rac_short_name, rac_type]]
_REDUNDANCY = [["1", "1", "2"], ["2", "2", "2"]]
_POWER_UNITS = [
    ["1", "3", "9", "PS1 Status"],
    ["2", "5", "9", "PS2 Status"],
]
# Devices that name their generation in racShortName but do not answer racType.
_SHORT_NAME_ONLY_IDRAC10 = [["iDRAC10", ""]]
_SHORT_NAME_ONLY_IDRAC9 = [["iDRAC9", ""]]
_RAC_INFO_UNNAMED_IDRAC9 = [["iDRAC", "80"]]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
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
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
            [Result(state=State.OK, summary="Status: full")],
            id="racShortName iDRAC10: status 1 -> full (OK)",
        ),
        pytest.param(
            "2",
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
            [Result(state=State.CRIT, summary="Status: lost")],
            id="racShortName iDRAC10: status 2 -> lost (CRIT)",
        ),
        pytest.param(
            "1",
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC9],
            [Result(state=State.UNKNOWN, summary="Status: other")],
            id="racShortName iDRAC9: status 1 -> other (UNKNOWN)",
        ),
        pytest.param(
            "2",
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC9],
            [Result(state=State.UNKNOWN, summary="Status: unknown")],
            id="racShortName iDRAC9: status 2 -> unknown (UNKNOWN)",
        ),
        pytest.param(
            "1",
            [_REDUNDANCY, _POWER_UNITS, []],
            [Result(state=State.OK, summary="Status: full")],
            id="no racInfo at all falls back to v4",
        ),
        pytest.param(
            "3",
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
            [],
            id="unknown item yields no result",
        ),
    ],
)
def test_check_dell_idrac_power(  # type: ignore[misc]
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
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
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
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
            [
                Result(state=State.OK, summary="Status: OK"),
                Result(state=State.OK, summary="Type: AC"),
                Result(state=State.OK, summary="Name: PS1 Status"),
            ],
            id="status 3 (OK), type 9 (AC)",
        ),
        pytest.param(
            "2",
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
            [
                Result(state=State.CRIT, summary="Status: CRITICAL"),
                Result(state=State.OK, summary="Type: AC"),
                Result(state=State.OK, summary="Name: PS2 Status"),
            ],
            id="status 5 (CRITICAL), type 9 (AC)",
        ),
        pytest.param(
            "3",
            [_REDUNDANCY, _POWER_UNITS, _SHORT_NAME_ONLY_IDRAC10],
            [],
            id="unknown item yields no result",
        ),
    ],
)
def test_check_dell_idrac_power_unit(  # type: ignore[misc]
    item: str,
    string_table: Sequence[StringTable],
    expected_results: Sequence[Any],
) -> None:
    """Test check function for dell_idrac_power_unit check."""
    parsed = parse_dell_idrac_power(string_table)
    result = list(check_dell_idrac_power_unit(item, parsed))
    assert result == expected_results


# Section of crash report 9aaa03be-7b12-11f1-ba68-bc2411416c01 (CMK-37257): the iDRAC answers
# powerSupplyIndex for two power supplies and nothing for their status, type and name.
_CRASH_SECTION: list[StringTable] = [
    [["1", "1", "0"]],
    [["1", "", "", ""], ["2", "", "", ""]],
    [],
]


def test_power_supply_without_reported_status_is_still_discovered() -> None:
    section = parse_dell_idrac_power(_CRASH_SECTION)

    services = list(discover_dell_idrac_power_unit(section))

    assert services == [Service(item="1"), Service(item="2")]


def test_power_supply_without_reported_status_says_the_device_did_not_report_it() -> None:
    section = parse_dell_idrac_power(_CRASH_SECTION)

    results = list(check_dell_idrac_power_unit("1", section))

    assert results == [Result(state=State.UNKNOWN, summary="Status: not reported by the device")]


def test_power_unit_without_reported_redundancy_status_says_the_device_did_not_report_it() -> None:
    section = parse_dell_idrac_power([[["1", "", "2"]], [], []])

    results = list(check_dell_idrac_power("1", section))

    assert results == [Result(state=State.UNKNOWN, summary="Status: not reported by the device")]


def test_power_supply_reports_only_the_values_the_device_delivers() -> None:
    section = parse_dell_idrac_power([_REDUNDANCY, [["1", "3", "", ""]], []])

    results = list(check_dell_idrac_power_unit("1", section))

    assert results == [Result(state=State.OK, summary="Status: OK")]


def test_power_supply_without_reported_index_is_not_discovered() -> None:
    section = parse_dell_idrac_power([_REDUNDANCY, [["", "3", "9", "PS1"]], []])

    services = list(discover_dell_idrac_power_unit(section))

    assert services == []


def test_power_unit_without_reported_index_is_not_discovered() -> None:
    section = parse_dell_idrac_power([[["", "1", "2"]], [], []])

    services = list(discover_dell_idrac_power(section))

    assert services == []


def test_rac_type_identifies_a_generation_the_short_name_omits() -> None:
    section = parse_dell_idrac_power([[["1", "3", "0"]], [], _RAC_INFO_UNNAMED_IDRAC9])

    results = list(check_dell_idrac_power("1", section))

    assert results == [Result(state=State.OK, summary="Status: full")]


@pytest.mark.parametrize(
    "rac_type, status",
    [
        pytest.param("16", "3", id="idrac7monolithic"),
        pytest.param("21", "3", id="idrac7DCS"),
        pytest.param("32", "3", id="idrac8monolithic"),
        pytest.param("48", "3", id="idrac9Monolithic"),
        pytest.param("64", "3", id="idrac915GMonolithic"),
        pytest.param("80", "3", id="idrac916GMonolithic"),
        pytest.param("96", "1", id="idrac1017GMonolithic"),
        pytest.param("98", "1", id="idrac1017GDCS"),
    ],
)
def test_rac_type_selects_the_value_scope_of_the_redundancy_status(
    rac_type: str, status: str
) -> None:
    """Both value scopes name a fully redundant power unit, but under different values."""
    section = parse_dell_idrac_power([[["1", status, "0"]], [], [["", rac_type]]])

    results = list(check_dell_idrac_power("1", section))

    assert results == [Result(state=State.OK, summary="Status: full")]


def test_rac_type_takes_precedence_over_the_short_name() -> None:
    section = parse_dell_idrac_power([[["1", "0", "0"]], [], [["iDRAC9", "96"]]])

    results = list(check_dell_idrac_power("1", section))

    assert results == [Result(state=State.OK, summary="Status: not redundant")]


@pytest.mark.parametrize("rac_type", ["1", "2", ""], ids=["other", "unknown", "not reported"])
def test_rac_type_without_a_generation_falls_back_to_the_short_name(rac_type: str) -> None:
    section = parse_dell_idrac_power([[["1", "3", "0"]], [], [["iDRAC9", rac_type]]])

    results = list(check_dell_idrac_power("1", section))

    assert results == [Result(state=State.OK, summary="Status: full")]


def test_falls_back_to_the_latest_mib_when_no_signal_names_a_generation() -> None:
    # Neither racType nor racShortName carries a generation, so the value scope cannot be
    # derived and the latest MIB (v4) is assumed, under which "1" is full.
    section = parse_dell_idrac_power([[["1", "1", "0"]], [], [["iDRAC", ""]]])

    results = list(check_dell_idrac_power("1", section))

    assert results == [Result(state=State.OK, summary="Status: full")]


@pytest.mark.parametrize(
    "rac_info, status, expected_summary",
    [
        pytest.param(
            [["iDRAC10", "96"]],
            "3",
            "Status: undefined value 3 (assuming the MIB for iDRAC10 or newer)",
            id="v3 value under the iDRAC10 MIB",
        ),
        pytest.param(
            [["iDRAC9", "48"]],
            "0",
            "Status: undefined value 0 (assuming the MIB for iDRAC9 or older)",
            id="v4 value under the iDRAC9 MIB",
        ),
    ],
)
def test_undefined_redundancy_status_names_the_value_and_the_assumed_mib(
    rac_info: StringTable, status: str, expected_summary: str
) -> None:
    section = parse_dell_idrac_power([[["1", status, "0"]], [], rac_info])

    results = list(check_dell_idrac_power("1", section))

    assert results == [Result(state=State.UNKNOWN, summary=expected_summary)]


def test_undefined_redundancy_status_leaves_the_power_supplies_readable() -> None:
    section = parse_dell_idrac_power(
        [[["1", "3", "0"]], [["1", "3", "9", "PS1 Status"]], [["iDRAC10", "96"]]]
    )

    results = list(check_dell_idrac_power_unit("1", section))

    assert results == [
        Result(state=State.OK, summary="Status: OK"),
        Result(state=State.OK, summary="Type: AC"),
        Result(state=State.OK, summary="Name: PS1 Status"),
    ]
