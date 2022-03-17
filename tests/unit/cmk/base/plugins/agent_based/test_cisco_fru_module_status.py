#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

check_name = "cisco_fru_module_status"


info = [
    [
        ["32", "Fabric card module", "9", "Fabric card module"],
        ["149", "Nexus7700 C7706 (6 Slot) Chassis", "3", "Nexus7700 C7706 (6 Slot) Chassis"],
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


@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"parse_{check_name}")
def _get_parse_function(fix_register):
    return fix_register.snmp_sections[SectionName(check_name)].parse_function


def test_parse_cisco_fru_module_status(parse_cisco_fru_module_status) -> None:
    assert parse_cisco_fru_module_status(info) == {
        "32": {"name": "Fabric card module", "state": (0, "OK")}
    }
