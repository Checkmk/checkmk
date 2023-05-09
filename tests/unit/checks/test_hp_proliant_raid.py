#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


@pytest.fixture(name="check_plugin")
def check_plugin_from_fix_register(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("hp_proliant_raid")]


@pytest.fixture(name="section_plugin")
def section_plugin_from_fix_register(fix_register: FixRegister) -> SNMPSectionPlugin:
    return fix_register.snmp_sections[SectionName("hp_proliant_raid")]


@pytest.fixture(name="string_table")
def snmp_section():
    return [
        [
            ["1", "", "2", "286070", "4294967295"],
            ["2", "", "2", "25753986", "4294967295"],
            ["3", "", "2", "30523320", "4294967295"],
            ["4", "", "2", "15", "4294967295"],
            ["5", "", "2", "15", "4294967295"],
            ["6", "", "2", "17169273", "4294967295"],
        ],
    ]


def test_discover_hp_proliant_raid_no_snmp_data(
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
) -> None:
    assert list(check_plugin.discovery_function({})) == []


def test_discover_hp_proliant_raid_aa(
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
    string_table,
) -> None:
    discovery_results = list(
        check_plugin.discovery_function(section_plugin.parse_function(string_table))
    )
    assert discovery_results == [
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
        Service(item="4"),
        Service(item="5"),
        Service(item="6"),
    ]


def test_check_hp_proliant_raid_item_not_found(
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
    string_table,
) -> None:
    assert (
        list(
            check_plugin.check_function(
                item="!111elf",
                params={},
                section=section_plugin.parse_function(string_table),
            )
        )
        == []
    )


def test_check_hp_proliant_raid(
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
    string_table,
) -> None:
    assert list(
        check_plugin.check_function(
            item="1",
            params={},
            section=section_plugin.parse_function(string_table),
        )
    ) == [
        Result(state=State.OK, summary="Status: OK"),
        Result(state=State.OK, summary="Logical volume size: 279.37 GB"),
    ]


def test_check_hp_proliant_raid_progress_cannot_be_determined(
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
) -> None:
    assert list(
        check_plugin.check_function(
            item="banana 1",
            params={},
            section=section_plugin.parse_function(
                [
                    [
                        ["1", "banana", "7", "286070", "4294967295"],
                    ],
                ]
            ),
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Status: rebuilding",
        ),
        Result(
            state=State.OK,
            summary="Logical volume size: 279.37 GB",
        ),
        Result(
            state=State.OK,
            summary="Rebuild: undetermined",
        ),
    ]
