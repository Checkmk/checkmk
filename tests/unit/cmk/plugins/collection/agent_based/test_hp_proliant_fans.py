#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.hp_proliant_fans import (
    check_plugin_hp_proliant_fans,
    DISCLAIMER,
    Section,
    snmp_section_hp_proliant_fans,
)

STRING_TABLE = [
    ["1", "3", "3", "2", "2", ""],
    ["2", "3", "3", "34", "2", ""],
]


def _section() -> Section:
    assert (section := snmp_section_hp_proliant_fans.parse_function([STRING_TABLE])) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_hp_proliant_fans.discovery_function(_section())) == [
        Service(item="1 (system)"),
        Service(item="2 (system)"),
    ]


def test_check_speed_state() -> None:
    assert list(check_plugin_hp_proliant_fans.check_function("1 (system)", _section())) == [
        Result(state=State.OK, summary="Status: ok"),
        Result(state=State.OK, summary="Speed: normal", details=f"Speed: normal\n{DISCLAIMER}"),
    ]


def test_check_speed_percentage() -> None:
    assert list(check_plugin_hp_proliant_fans.check_function("2 (system)", _section())) == [
        Result(state=State.OK, summary="Status: ok"),
        Result(state=State.OK, summary="Speed: 34%", details=f"Speed: 34%\n{DISCLAIMER}"),
    ]
