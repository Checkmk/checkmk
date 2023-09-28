#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.citrix_state import (
    check_citrix_state,
    check_citrix_state_controller,
    check_citrix_state_hosting_server,
    DEFAULT_PARAMS,
)
from cmk.base.plugins.agent_based.inventory_citrix_state import inventory_citrix_state
from cmk.base.plugins.agent_based.utils.citrix_state import parse_citrix_state

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
    section = parse_citrix_state(STRING_TABLE)
    expected = [v1.Result(state=v1.State.OK, summary="rz1cdc02.intern.kasse")]
    assert list(check_citrix_state_controller(section)) == expected


def test_check_citrix_state_hosting_server() -> None:
    section = parse_citrix_state(STRING_TABLE)
    expected = [v1.Result(state=v1.State.OK, summary="rz1xen03.intern.kasse")]
    assert list(check_citrix_state_hosting_server(section)) == expected


def test_check_citrix_state_() -> None:
    section = parse_citrix_state(STRING_TABLE)
    expected = [
        v1.Result(state=v1.State.OK, summary="FaultState None"),
        v1.Result(state=v1.State.OK, summary="MaintenanceMode False"),
        v1.Result(state=v1.State.OK, summary="PowerState On"),
        v1.Result(state=v1.State.OK, summary="RegistrationState Registered"),
        v1.Result(state=v1.State.OK, summary="VMToolsState Running"),
    ]
    assert list(check_citrix_state(DEFAULT_PARAMS, section)) == expected
