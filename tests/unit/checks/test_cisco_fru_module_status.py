#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Service, Result, State
import cmk.base.api.agent_based.register as agent_based_register
from cmk.utils.type_defs import CheckPluginName, SectionName


@pytest.fixture(name="section_plugin")
def fixture_section_plugin() -> SNMPSectionPlugin:
    return agent_based_register.get_snmp_section_plugin(SectionName("cisco_fru_module_status"))


@pytest.fixture(name="check_plugin")
def fixture_check_plugin() -> CheckPlugin:
    plugin = agent_based_register.get_check_plugin(CheckPluginName("cisco_fru_module_status"))
    assert plugin
    return plugin


@pytest.mark.usefixtures("config_load_all_checks")
def test_parse(section_plugin: SNMPSectionPlugin) -> None:
    assert section_plugin.parse_function([
        [
            ["32", "Fabric card module", "9", "Fabric card module"],
            [
                "149",
                "Nexus7700 C7706 (6 Slot) Chassis",
                "3",
                "Nexus7700 C7706 (6 Slot) Chassis",
            ],
            ["214", "LinecardSlot-1", "5", "LinecardSlot-1"],
            ["406", "Backplane", "4", "Backplane"],
            ["470", "N77-AC-3KW PS-1", "6", "PowerSupply-1"],
            ["534", "Fan Module-1", "7", "Fan Module-1"],
            ["598", "module-1 processor-1", "1", "module-1 processor-1"],
            ["4950", "Linecard-1 Port-1", "10", "Linecard-1 Port-1"],
        ],
        [
            ["32", "2"],
        ],
    ]) == {
        "32": {
            "name": "Fabric card module",
            "state": (0, "OK")
        },
    }


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover(check_plugin: CheckPlugin) -> None:
    assert list(
        check_plugin.discovery_function({
            "32": {
                "name": "Fabric card module",
                "state": (0, "OK")
            },
        })) == [Service(item="32")]


@pytest.mark.usefixtures("config_load_all_checks")
def test_check(check_plugin: CheckPlugin) -> None:
    assert list(
        check_plugin.check_function(
            item="32",
            params={},
            section={
                "32": {
                    "name": "Fabric card module",
                    "state": (0, "OK")
                },
            },
        )) == [
            Result(state=State.OK, summary="[Fabric card module] Operational status: OK"),
        ]
