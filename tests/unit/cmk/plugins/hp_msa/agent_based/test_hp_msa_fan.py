#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hp_msa.agent_based.hp_msa_fan import (
    agent_section_hp_msa_fan,
    check_plugin_hp_msa_fan,
)
from cmk.plugins.hp_msa.agent_based.lib import Section


def _section() -> Section:
    assert (
        section := agent_section_hp_msa_fan.parse_function(
            [
                ["fan", "2", "durable-id", "fan_1.1"],
                ["fan", "2", "name", "Fan", "Loc:left-PSU", "1"],
                ["fan", "2", "location", "Enclosure", "1", "-", "Left"],
                ["fan", "2", "status-ses", "OK"],
                ["fan", "2", "status-ses-numeric", "1"],
                ["fan", "2", "extended-status", "16"],
                ["fan", "2", "status", "Up"],
                ["fan", "2", "status-numeric", "0"],
                ["fan", "2", "speed", "3780"],
                ["fan", "2", "position", "Left"],
                ["fan", "2", "position-numeric", "0"],
                ["fan", "2", "serial-number", "N/A"],
                ["fan", "2", "part-number", "N/A"],
                ["fan", "2", "fw-revision"],
                ["fan", "2", "hw-revision"],
                ["fan", "2", "locator-led", "Off"],
                ["fan", "2", "locator-led-numeric", "0"],
                ["fan", "2", "health", "OK"],
                ["fan", "2", "health-numeric", "0"],
                ["fan", "2", "health-reason"],
                ["fan", "2", "health-recommendation"],
                ["fan", "4", "durable-id", "fan_1.2"],
                ["fan", "4", "name", "Fan", "Loc:right-PSU", "2"],
                ["fan", "4", "location", "Enclosure", "1", "-", "Right"],
                ["fan", "4", "status-ses", "OK"],
                ["fan", "4", "status-ses-numeric", "1"],
                ["fan", "4", "extended-status", "16"],
                ["fan", "4", "status", "Up"],
                ["fan", "4", "status-numeric", "0"],
                ["fan", "4", "speed", "3840"],
                ["fan", "4", "position", "Right"],
                ["fan", "4", "position-numeric", "1"],
                ["fan", "4", "serial-number", "N/A"],
                ["fan", "4", "part-number", "N/A"],
                ["fan", "4", "fw-revision"],
                ["fan", "4", "hw-revision"],
                ["fan", "4", "locator-led", "Off"],
                ["fan", "4", "locator-led-numeric", "0"],
                ["fan", "4", "health", "OK"],
                ["fan", "4", "health-numeric", "0"],
                ["fan", "4", "health-reason"],
                ["fan", "4", "health-recommendation"],
            ]
        )
    )
    return section


def test_discovery() -> None:
    assert list(check_plugin_hp_msa_fan.discovery_function(_section())) == [
        Service(item="Enclosure 1 Left"),
        Service(item="Enclosure 1 Right"),
    ]


def test_check() -> None:
    assert list(
        check_plugin_hp_msa_fan.check_function(
            "Enclosure 1 Left",
            _section(),
        )
    ) == [Result(state=State.OK, summary="Status: up, speed: 3780 RPM")]
