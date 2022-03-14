#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Sequence

import pytest

from tests.testlib import on_time

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.utils.inventory_interfaces import (
    Interface,
    inventorize_interfaces,
    InventoryParams,
)

from ..utils_inventory import sort_inventory_result


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
                        "description": "Vlan-interface1",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "port-channel 1",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "AUX0",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "gigabitEthernet 1/0/1",
                        "alias": "Uplink sw-ks-01",
                    },
                    inventory_columns={
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
                        "description": "Vlan-interface1",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "port-channel 1",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "AUX0",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "gigabitEthernet 1/0/1",
                        "alias": "Uplink sw-ks-01",
                    },
                    inventory_columns={
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
                        "available_ethernet_ports": 0,
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
                        "description": "Vlan-interface1",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "port-channel 1",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "AUX0",
                        "alias": "",
                    },
                    inventory_columns={
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
                        "description": "gigabitEthernet 1/0/1",
                        "alias": "Uplink sw-ks-01",
                    },
                    inventory_columns={
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
    mocker,
    params: InventoryParams,
    interfaces: Sequence[Interface],
    n_total: int,
    uptime_sec: Optional[float],
    expected_result: InventoryResult,
) -> None:
    with on_time(500000, "UTC"):
        assert sort_inventory_result(
            inventorize_interfaces(
                params,
                interfaces,
                n_total,
                uptime_sec,
            )
        ) == sort_inventory_result(expected_result)
