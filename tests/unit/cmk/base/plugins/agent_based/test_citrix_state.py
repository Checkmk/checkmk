#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.legacy_checks import citrix_state as legacy
from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.inventory_citrix_state import (
    inventory_citrix_state,
    parse_citrix_state,
)

from .utils_inventory import sort_inventory_result

STRING_TABLE = [
    ["Catalog", "XenApp", "-", "Standard", "-", "RZ1"],
    ["Controller", "rz1cdc02.intern.kasse"],
    ["DesktopGroupName", "XenApp", "-", "Standard"],
    ["FaultState", "None"],
    ["HostingServer", "rz1xen03.intern.kasse"],
    ["MaintenanceMode", "False"],
    ["PowerState", "On"],
    ["RegistrationState", "Registered"],
    ["VMToolsState", "Running"],
    ["AgentVersion", "7.6.0.5026"],
    ["Catalog", "XenApp", "-", "Standard", "-", "RZ1"],
    ["Controller", "rz1cdc02.intern.kasse"],
    ["DesktopGroupName", "XenApp", "-", "Standard"],
    ["FaultState", "None"],
    ["HostingServer", "rz1xen03.intern.kasse"],
    ["MaintenanceMode", "False"],
    ["PowerState", "On"],
    ["RegistrationState", "Registered"],
    ["VMToolsState", "Running"],
    ["AgentVersion", "7.6.0.5026"],
]


def test_inventory_citrix_state() -> None:
    section = parse_citrix_state(STRING_TABLE)
    expected = v1.Attributes(
        path=["software", "applications", "citrix", "vm"],
        inventory_attributes={
            "desktop_group_name": "XenApp - Standard",
            "catalog": "XenApp - Standard - RZ1",
            "agent_version": "7.6.0.5026",
        },
        status_attributes={},
    )
    assert sort_inventory_result(inventory_citrix_state(section)) == [expected]


def test_check_citrix_state_controller() -> None:
    section = legacy.parse_citrix_state(STRING_TABLE)
    expected = [0, "rz1cdc02.intern.kasse"]
    assert list(legacy.check_citrix_state_controller(None, None, section)) == expected


def test_check_citrix_state_hosting_server() -> None:
    section = legacy.parse_citrix_state(STRING_TABLE)
    expected = [0, "rz1xen03.intern.kasse"]
    assert list(legacy.check_citrix_state_hosting_server(None, None, section)) == expected


def test_check_citrix_state_() -> None:
    section = legacy.parse_citrix_state(STRING_TABLE)
    expected = [
        (0, "FaultState: None"),
        (0, "MaintenanceMode: False"),
        (0, "PowerState: On"),
        (0, "RegistrationState: Registered"),
        (0, "VMToolsState: Running"),
    ]
    assert list(legacy.check_citrix_state(None, {}, section)) == expected
