#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import InventoryResult
from cmk.base.plugins.agent_based.inventory_statgrab_net import (
    inventory_statgrab_net,
    parse_statgrab_net,
)
from cmk.base.plugins.agent_based.utils.interfaces import Interface, Section

from .utils_inventory import sort_inventory_result

_SECTION = [
    Interface(
        index="1",
        descr="lo0",
        alias="lo0",
        type="24",
        speed=0,
        oper_status="1",
        in_octets=0,
        in_ucast=0,
        in_mcast=0,
        in_bcast=0,
        in_discards=0,
        in_errors=0,
        out_octets=0,
        out_ucast=0,
        out_mcast=0,
        out_bcast=0,
        out_discards=0,
        out_errors=0,
        out_qlen=0,
        phys_address="",
        oper_status_name="up",
        speed_as_text="",
        group=None,
        node=None,
        admin_status=None,
        total_octets=0,
    ),
    Interface(
        index="2",
        descr="mac",
        alias="mac",
        type="6",
        speed=0,
        oper_status="2",
        in_octets=125659024941,
        in_ucast=50729410,
        in_mcast=0,
        in_bcast=0,
        in_discards=0,
        in_errors=0,
        out_octets=482272878,
        out_ucast=102,
        out_mcast=0,
        out_bcast=0,
        out_discards=0,
        out_errors=0,
        out_qlen=0,
        phys_address="",
        oper_status_name="down",
        speed_as_text="",
        group=None,
        node=None,
        admin_status=None,
        total_octets=126141297819,
    ),
    Interface(
        index="3",
        descr="vnet0",
        alias="vnet0",
        type="6",
        speed=10000000,
        oper_status="1",
        in_octets=125659024941,
        in_ucast=1268296097,
        in_mcast=0,
        in_bcast=0,
        in_discards=0,
        in_errors=0,
        out_octets=19679032546569,
        out_ucast=13022050069,
        out_mcast=0,
        out_bcast=0,
        out_discards=0,
        out_errors=0,
        out_qlen=0,
        phys_address="",
        oper_status_name="up",
        speed_as_text="",
        group=None,
        node=None,
        admin_status=None,
        total_octets=19804691571510,
        extra_info=None,
    ),
]


def test_parse_statgrab_net() -> None:
    assert (
        parse_statgrab_net(
            [
                ["lo0.duplex", "unknown"],
                ["lo0.interface_name", "lo0"],
                ["lo0.speed", "0"],
                ["lo0.up", "true"],
                ["mac.collisions", "0"],
                ["mac.collisions", "0"],
                ["mac.collisions", "0"],
                ["mac.collisions", "0"],
                ["mac.ierrors", "0"],
                ["mac.ierrors", "0"],
                ["mac.ierrors", "0"],
                ["mac.ierrors", "0"],
                ["mac.interface_name", "mac"],
                ["mac.interface_name", "mac"],
                ["mac.interface_name", "mac"],
                ["mac.interface_name", "mac"],
                ["mac.ipackets", "1268296097"],
                ["mac.ipackets", "38927952"],
                ["mac.ipackets", "565577805"],
                ["mac.ipackets", "50729410"],
                ["mac.oerrors", "0"],
                ["mac.oerrors", "0"],
                ["mac.oerrors", "0"],
                ["mac.oerrors", "0"],
                ["mac.opackets", "565866338"],
                ["mac.opackets", "8035845"],
                ["mac.opackets", "13022050069"],
                ["mac.opackets", "102"],
                ["mac.rx", "8539777403"],
                ["mac.rx", "9040025900"],
                ["mac.rx", "144543115933"],
                ["mac.rx", "125659024941"],
                ["mac.systime", "1413287036"],
                ["mac.systime", "1413287036"],
                ["mac.systime", "1413287036"],
                ["mac.systime", "1413287036"],
                ["mac.tx", "15206"],
                ["mac.tx", "19679032546569"],
                ["mac.tx", "124614022405"],
                ["mac.tx", "482272878"],
                ["vnet0.collisions", "0"],
                ["vnet0.duplex", "unknown"],
                ["vnet0.ierrors", "0"],
                ["vnet0.interface_name", "vnet0"],
                ["vnet0.ipackets", "1268296097"],
                ["vnet0.oerrors", "0"],
                ["vnet0.opackets", "13022050069"],
                ["vnet0.rx", "125659024941"],
                ["vnet0.speed", "10"],
                ["vnet0.systime", "1413287036"],
                ["vnet0.tx", "19679032546569"],
                ["vnet0.up", "true"],
            ]
        )
        == _SECTION
    )


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            [],
            [],
        ),
        (
            _SECTION,
            [
                TableRow(
                    path=["networking", "interfaces"],
                    key_columns={
                        "index": 3,
                        "description": "vnet0",
                        "alias": "vnet0",
                    },
                    inventory_columns={
                        "speed": 10000000,
                        "phys_address": "",
                        "oper_status": 1,
                        "port_type": 6,
                        "available": False,
                    },
                    status_columns={},
                ),
                Attributes(
                    path=["networking"],
                    inventory_attributes={
                        "available_ethernet_ports": 0,
                        "total_ethernet_ports": 1,
                        "total_interfaces": 3,
                    },
                    status_attributes={},
                ),
            ],
        ),
    ],
)
def test_inventory_statgrab_net(
    section: Section,
    expected_result: InventoryResult,
) -> None:
    assert sort_inventory_result(inventory_statgrab_net(section)) == sort_inventory_result(
        expected_result
    )
