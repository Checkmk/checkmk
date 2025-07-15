#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Sequence
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pytest_mock import MockerFixture

from cmk.agent_based.v2 import Attributes, InventoryResult, TableRow
from cmk.plugins.lib.inventory_interfaces import Interface, inventorize_interfaces, InventoryParams
from tests.unit.cmk.plugins.collection.agent_based.utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "params, interfaces, n_total, uptime_sec, expected_result",
    [
        pytest.param(
            {},
            [
                Interface(
                    index="1",
                    descr="Vlan-interface1",
                    alias="",
                    type="6",
                    speed=0,
                    oper_status=2,
                    phys_address="74:DA:88:58:16:11",
                ),
                Interface(
                    index="32769",
                    descr="port-channel 1",
                    alias="",
                    type="6",
                    speed=1000000000,
                    oper_status=1,
                    phys_address="74:DA:88:58:16:11",
                ),
                Interface(
                    index="49152",
                    descr="AUX0",
                    alias="",
                    type="23",
                    speed=0,
                    oper_status=1,
                    phys_address="",
                ),
                Interface(
                    index="49153",
                    descr="gigabitEthernet 1/0/1",
                    alias="Uplink sw-ks-01",
                    type="6",
                    speed=1000000000,
                    oper_status=2,
                    phys_address="74:DA:88:58:16:11",
                ),
            ],
            4,
            None,
            [
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 1,
                    },
                    inventory_columns={
                        "description": "Vlan-interface1",
                        "alias": "",
                        "speed": 0,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 2,
                        "port_type": 6,
                        "available": True,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 32769,
                    },
                    inventory_columns={
                        "description": "port-channel 1",
                        "alias": "",
                        "speed": 1000000000,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 1,
                        "port_type": 6,
                        "available": False,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 49152,
                    },
                    inventory_columns={
                        "description": "AUX0",
                        "alias": "",
                        "speed": 0,
                        "phys_address": "",
                        "oper_status": 1,
                        "port_type": 23,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 49153,
                    },
                    inventory_columns={
                        "description": "gigabitEthernet 1/0/1",
                        "alias": "Uplink sw-ks-01",
                        "speed": 1000000000,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 2,
                        "port_type": 6,
                        "available": True,
                    },
                    status_columns={},
                ),
                Attributes(
                    path=["networking"],
                    inventory_attributes={
                        "available_ethernet_ports": 2,
                        "total_ethernet_ports": 3,
                        "total_interfaces": 4,
                    },
                    status_attributes={},
                ),
            ],
            id="no uptime, no params",
        ),
        pytest.param(
            {"usage_port_types": ["46"]},
            [
                Interface(
                    index="1",
                    descr="Vlan-interface1",
                    alias="",
                    type="6",
                    speed=0,
                    oper_status=2,
                    phys_address="74:DA:88:58:16:11",
                    admin_status=2,
                ),
                Interface(
                    index="32769",
                    descr="port-channel 1",
                    alias="",
                    type="6",
                    speed=1000000000,
                    oper_status=1,
                    phys_address="74:DA:88:58:16:11",
                    admin_status=2,
                ),
                Interface(
                    index="49152",
                    descr="AUX0",
                    alias="",
                    type="23",
                    speed=0,
                    oper_status=1,
                    phys_address="",
                    admin_status=2,
                ),
                Interface(
                    index="49153",
                    descr="gigabitEthernet 1/0/1",
                    alias="Uplink sw-ks-01",
                    type="6",
                    speed=1000000000,
                    oper_status=2,
                    phys_address="74:DA:88:58:16:11",
                    admin_status=2,
                ),
            ],
            5,
            None,
            [
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 1,
                    },
                    inventory_columns={
                        "description": "Vlan-interface1",
                        "alias": "",
                        "speed": 0,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 2,
                        "port_type": 6,
                        "admin_status": 2,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 32769,
                    },
                    inventory_columns={
                        "description": "port-channel 1",
                        "alias": "",
                        "speed": 1000000000,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 1,
                        "port_type": 6,
                        "admin_status": 2,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 49152,
                    },
                    inventory_columns={
                        "description": "AUX0",
                        "alias": "",
                        "speed": 0,
                        "phys_address": "",
                        "oper_status": 1,
                        "port_type": 23,
                        "admin_status": 2,
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 49153,
                    },
                    inventory_columns={
                        "description": "gigabitEthernet 1/0/1",
                        "alias": "Uplink sw-ks-01",
                        "speed": 1000000000,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 2,
                        "port_type": 6,
                        "admin_status": 2,
                    },
                    status_columns={},
                ),
                Attributes(
                    path=["networking"],
                    inventory_attributes={
                        "total_ethernet_ports": 0,
                        "total_interfaces": 5,
                    },
                    status_attributes={},
                ),
            ],
            id="custom usage_port_types",
        ),
        pytest.param(
            {"unused_duration": 60},
            [
                Interface(
                    index="1",
                    descr="Vlan-interface1",
                    alias="",
                    type="6",
                    speed=0,
                    oper_status=2,
                    phys_address="74:DA:88:58:16:11",
                    admin_status=2,
                    last_change=456,
                ),
                Interface(
                    index="32769",
                    descr="port-channel 1",
                    alias="",
                    type="6",
                    speed=1000000000,
                    oper_status=1,
                    phys_address="74:DA:88:58:16:11",
                    admin_status=2,
                    last_change=20,
                ),
                Interface(
                    index="49152",
                    descr="AUX0",
                    alias="",
                    type="23",
                    speed=0,
                    oper_status=1,
                    phys_address="",
                    admin_status=2,
                    last_change=30,
                ),
                Interface(
                    index="49153",
                    descr="gigabitEthernet 1/0/1",
                    alias="Uplink sw-ks-01",
                    type="6",
                    speed=1000000000,
                    oper_status=2,
                    phys_address="74:DA:88:58:16:11",
                    admin_status=2,
                    last_change=40,
                ),
            ],
            4,
            500,
            [
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 1,
                    },
                    inventory_columns={
                        "description": "Vlan-interface1",
                        "alias": "",
                        "speed": 0,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 2,
                        "port_type": 6,
                        "admin_status": 2,
                        "available": False,
                    },
                    status_columns={"last_change": 432000},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 32769,
                    },
                    inventory_columns={
                        "description": "port-channel 1",
                        "alias": "",
                        "speed": 1000000000,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 1,
                        "port_type": 6,
                        "admin_status": 2,
                        "available": False,
                    },
                    status_columns={"last_change": 432000},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 49152,
                    },
                    inventory_columns={
                        "description": "AUX0",
                        "alias": "",
                        "speed": 0,
                        "phys_address": "",
                        "oper_status": 1,
                        "port_type": 23,
                        "admin_status": 2,
                    },
                    status_columns={"last_change": 432000},
                ),
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 49153,
                    },
                    inventory_columns={
                        "description": "gigabitEthernet 1/0/1",
                        "alias": "Uplink sw-ks-01",
                        "speed": 1000000000,
                        "phys_address": "74:DA:88:58:16:11",
                        "oper_status": 2,
                        "port_type": 6,
                        "admin_status": 2,
                        "available": True,
                    },
                    status_columns={"last_change": 432000},
                ),
                Attributes(
                    path=["networking"],
                    inventory_attributes={
                        "available_ethernet_ports": 1,
                        "total_ethernet_ports": 3,
                        "total_interfaces": 4,
                    },
                    status_attributes={},
                ),
            ],
            id="with uptime",
        ),
    ],
)
def test_inventorize_interfaces(
    mocker: MockerFixture,
    params: InventoryParams,
    interfaces: Sequence[Interface],
    n_total: int,
    uptime_sec: float | None,
    expected_result: InventoryResult,
) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(500000, tz=ZoneInfo("UTC"))):
        assert sort_inventory_result(
            inventorize_interfaces(
                params,
                interfaces,
                n_total,
                uptime_sec,
            )
        ) == sort_inventory_result(expected_result)
