#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.dell_idrac_power import (
    check_dell_idrac_power,
    check_dell_idrac_power_unit,
    discover_dell_idrac_power_unit,
    parse_dell_idrac_power,
)

# Section layout (see snmp_section_dell_idrac_power):
#   section[0]: power unit redundancy -> [index, status, count]
#   section[1]: power supply          -> [index, status, psu_type, location]
#   section[2]: firmware version      -> [[firmware_shortname]]
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
