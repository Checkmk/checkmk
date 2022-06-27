#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.vutlan_ems_smoke import SmokeSensor, SmokeSensorSection

pytestmark = pytest.mark.checks


def test_parse_vutlan_ems_smoke(fix_register: FixRegister) -> None:
    check = fix_register.snmp_sections[SectionName("vutlan_ems_smoke")]

    string_table = [
        [
            ["101001", "Dry-1", "0"],
            ["101002", "Dry-2", "0"],
            ["101003", "Dry-3", "0"],
            ["101004", "Dry-4", "0"],
            ["106001", "Analog-5", "0"],
            ["107001", "Analog-6", "0"],
            ["201001", "Onboard Temperature", "32.80"],
            ["201002", "Analog-1", "22.00"],
            ["201003", "Analog-2", "22.10"],
            ["202001", "Analog-3", "46.20"],
            ["202002", "Analog-4", "42.10"],
            ["203001", "Onboard Voltage DC", "12.06"],
            ["301001", "Analog Power", "on"],
            ["304001", "Power-1", "off"],
            ["304002", "Power-2", "off"],
            ["403001", "USB Web camera", "0"],
            ["106002", "Banana", "2"],
        ]
    ]
    result = check.parse_function(string_table)

    expected_parse_result = {
        "Analog-5": SmokeSensor(name="Analog-5", state=0),
        "Banana": SmokeSensor(name="Banana", state=2),
    }

    assert result == expected_parse_result


def test_parse_vutlan_ems_smoke_no_smoke_detector(fix_register: FixRegister) -> None:
    check = fix_register.snmp_sections[SectionName("vutlan_ems_smoke")]

    string_table = [
        [
            ["101001", "Dry-1", "0"],
            ["101002", "Dry-2", "0"],
            ["101003", "Dry-3", "0"],
            ["101004", "Dry-4", "0"],
            ["102001", "Analog-5", "0"],
            ["107001", "Analog-6", "0"],
            ["201001", "Onboard Temperature", "32.80"],
            ["201002", "Analog-1", "22.00"],
            ["201003", "Analog-2", "22.10"],
            ["202001", "Analog-3", "46.20"],
            ["202002", "Analog-4", "42.10"],
            ["203001", "Onboard Voltage DC", "12.06"],
            ["301001", "Analog Power", "on"],
            ["304001", "Power-1", "off"],
            ["304002", "Power-2", "off"],
            ["403001", "USB Web camera", "0"],
            ["103002", "Banana", "2"],
        ]
    ]
    result = check.parse_function(string_table)

    expected_parse_result: SmokeSensorSection = {}

    assert result == expected_parse_result


def test_section_vutlan_ems_smoke(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("vutlan_ems_smoke")]

    section = {
        "Analog-5": SmokeSensor(name="Analog-5", state=0),
        "Banana": SmokeSensor(name="Banana", state=2),
    }
    result = check.discovery_function(section=section)

    expected_section_result = [
        Service(item="Analog-5"),
        Service(item="Banana"),
    ]

    assert list(result) == expected_section_result


def test_check_vutlan_ems_smoke_state_crit(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("vutlan_ems_smoke")]

    section = {
        "Analog-5": SmokeSensor(name="Analog-5", state=0),
        "Banana": SmokeSensor(name="Banana", state=2),
    }

    result = check.check_function(item="Banana", section=section)

    expected_check_result_state_crit = [Result(state=State.CRIT, summary="Smoke detected")]

    assert list(result) == expected_check_result_state_crit

    section = {
        "Analog-5": SmokeSensor(name="Analog-5", state=0),
        "Banana": SmokeSensor(name="Banana", state=1),
    }

    result = check.check_function(item="Banana", section=section)

    expected_check_result_state_crit = [Result(state=State.CRIT, summary="Smoke detected")]

    assert list(result) == expected_check_result_state_crit


def test_check_vutlan_ems_smoke_state_ok(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("vutlan_ems_smoke")]
    section = {
        "Analog-5": SmokeSensor(name="Analog-5", state=0),
        "Banana": SmokeSensor(name="Banana", state=2),
    }

    result = check.check_function(item="Analog-5", section=section)

    expected_check_result_state_ok = [Result(state=State.OK, summary="No smoke detected")]

    assert list(result) == expected_check_result_state_ok


def test_check_vutlan_ems_smoke_item_not_found(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("vutlan_ems_smoke")]
    section = {
        "Analog-5": SmokeSensor(name="Analog-5", state=0),
    }

    result = check.check_function(item="Banana", section=section)

    assert list(result) == []
