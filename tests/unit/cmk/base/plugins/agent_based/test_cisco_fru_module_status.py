#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based import cisco_fru_module_status
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


@pytest.fixture(name="check_plugin")
def fixture_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("cisco_fru_module_status")]


def test_parse() -> None:
    assert cisco_fru_module_status.parse(
        [
            [
                ["32", "9", "Fabric card module"],
                ["149", "3", "Nexus7700 C7706 (6 Slot) Chassis"],
                ["214", "5", "LinecardSlot-1"],
                ["406", "4", "Backplane"],
                ["470", "6", "PowerSupply-1"],
                ["534", "7", "Fan Module-1"],
                ["598", "1", "module-1 processor-1"],
                ["4950", "10", "Linecard-1 Port-1"],
            ],
            [
                ["32", "2"],
            ],
        ]
    ) == {
        "32": cisco_fru_module_status.Module(state="2", name="Fabric card module"),
    }


def test_parse_invalid_phyiscal_class() -> None:
    assert (
        cisco_fru_module_status.parse(
            [
                [
                    ["9", "3", "CHASSIS-1"],
                    ["10", "0", ""],
                    ["11", "7", "FAN-1"],
                    ["12", "0", ""],
                    ["13", "0", ""],
                    ["14", "0", ""],
                    ["15", "6", "PSU-1"],
                    ["16", "0", ""],
                    ["17", "1", "MEMORY-1"],
                    ["18", "0", ""],
                    ["19", "0", ""],
                    ["20", "0", ""],
                    ["21", "1", "SSD-1"],
                    ["22", "0", ""],
                    ["23", "12", "CPU-1"],
                    ["24", "0", ""],
                    ["25", "0", ""],
                ],
                [],
            ]
        )
        == {}
    )


def test_discover(check_plugin: CheckPlugin) -> None:
    assert list(
        check_plugin.discovery_function(
            {
                "32": cisco_fru_module_status.Module(state="2", name="Fabric card module"),
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
                "32": cisco_fru_module_status.Module(state="2", name="Fabric card module"),
            },
        )
    ) == [
        Result(state=State.OK, summary="[Fabric card module] Operational status: OK"),
    ]
