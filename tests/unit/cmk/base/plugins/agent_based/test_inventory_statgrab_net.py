#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.inventory_statgrab_net import (
    inventory_statgrab_net,
    parse_statgrab_net,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
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
            ],
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
def test_inventory_statgrab_net(string_table, expected_result):
    assert list(inventory_statgrab_net(parse_statgrab_net(string_table))) == expected_result
