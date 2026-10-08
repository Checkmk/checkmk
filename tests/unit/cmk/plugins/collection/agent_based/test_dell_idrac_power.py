#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.dell_idrac_power import (
    check_dell_idrac_power,
    check_dell_idrac_power_unit,
    parse_dell_idrac_power,
)
from cmk.plugins.collection.agent_based.dell_idrac_power import (
    inventory_dell_idrac_power_unit as discover_dell_idrac_power_unit,
)

# Section layout (see snmp_section_dell_idrac_power):
#   section[0]: power unit redundancy -> [index, status, count]
#   section[1]: power supply          -> [index, status, psu_type, location]
#   section[2]: racInfoGroup scalars  -> [[rac_short_name, rac_type]]
#
# Section of crash report 9aaa03be-7b12-11f1-ba68-bc2411416c01 (CMK-37257): the iDRAC answers
# powerSupplyIndex for two power supplies and nothing for their status, type and name.
_CRASH_SECTION: Sequence[StringTable] = [
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
    section = parse_dell_idrac_power([[["1", "1", "2"]], [["1", "3", "", ""]], []])

    results = list(check_dell_idrac_power_unit("1", section))

    assert results == [Result(state=State.OK, summary="Status: OK")]


def test_power_supply_reports_all_the_values_the_device_delivers() -> None:
    section = parse_dell_idrac_power([[["1", "1", "2"]], [["1", "3", "9", "PS1 Status"]], []])

    results = list(check_dell_idrac_power_unit("1", section))

    assert results == [Result(state=State.OK, summary="Status: OK, Type: AC, Name: PS1 Status")]


def test_rac_type_identifies_a_generation_the_short_name_omits() -> None:
    section = parse_dell_idrac_power([[["1", "3", "0"]], [], [["iDRAC", "80"]]])

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


def test_falls_back_to_the_latest_mib_without_any_rac_info() -> None:
    section = parse_dell_idrac_power([[["1", "1", "0"]], [], []])

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
