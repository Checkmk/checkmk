#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.vutlan_ems_smoke import (
    check_plugin_vutlan_ems_smoke,
    SmokeSensor,
    snmp_section_vutlan_ems_smoke,
)


def test_parse_vutlan_ems_smoke() -> None:
    assert snmp_section_vutlan_ems_smoke.parse_function(
        [
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
    ) == {
        "Analog-5": SmokeSensor(name="Analog-5", state=0),
        "Banana": SmokeSensor(name="Banana", state=2),
    }


def test_parse_vutlan_ems_smoke_no_smoke_detector() -> None:
    assert (
        snmp_section_vutlan_ems_smoke.parse_function(
            [
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
        )
        == {}
    )


def test_section_vutlan_ems_smoke() -> None:
    assert list(
        check_plugin_vutlan_ems_smoke.discovery_function(
            {
                "Analog-5": SmokeSensor(name="Analog-5", state=0),
                "Banana": SmokeSensor(name="Banana", state=2),
            }
        )
    ) == [
        Service(item="Analog-5"),
        Service(item="Banana"),
    ]


def test_check_vutlan_ems_smoke_state_crit() -> None:
    assert list(
        check_plugin_vutlan_ems_smoke.check_function(
            "Banana",
            {
                "Analog-5": SmokeSensor(name="Analog-5", state=0),
                "Banana": SmokeSensor(name="Banana", state=2),
            },
        )
    ) == [Result(state=State.CRIT, summary="Smoke detected")]


def test_check_vutlan_ems_smoke_state_ok() -> None:
    assert list(
        check_plugin_vutlan_ems_smoke.check_function(
            "Analog-5",
            {
                "Analog-5": SmokeSensor(name="Analog-5", state=0),
                "Banana": SmokeSensor(name="Banana", state=2),
            },
        )
    ) == [Result(state=State.OK, summary="No smoke detected")]


def test_check_vutlan_ems_smoke_item_not_found() -> None:
    assert not list(
        check_plugin_vutlan_ems_smoke.check_function(
            "Banana",
            {
                "Analog-5": SmokeSensor(name="Analog-5", state=0),
            },
        )
    )
