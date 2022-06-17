#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


@pytest.fixture(name="check_plugin")
def fixture_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("cisco_fru_module_status")]


def test_parse(fix_register) -> None:
    assert fix_register.snmp_sections[SectionName("cisco_fru_module_status")].parse_function(
        [
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
        ]
    ) == {
        "32": {"name": "Fabric card module", "state": (0, "OK")},
    }


def test_discover(check_plugin: CheckPlugin) -> None:
    assert list(
        check_plugin.discovery_function(
            {
                "32": {"name": "Fabric card module", "state": (0, "OK")},
            }
        )
    ) == [
        Service(item="32"),
    ]


def test_check(check_plugin: CheckPlugin) -> None:
    assert list(
        check_plugin.check_function(
            item="32",
            params={},
            section={
                "32": {"name": "Fabric card module", "state": (0, "OK")},
            },
        )
    ) == [
        Result(state=State.OK, summary="[Fabric card module] Operational status: OK"),
    ]
