#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="inventory_netapp_api_info", scope="module")
def _inventory_netapp_api_info(fix_register):
    return fix_register.inventory_plugins[InventoryPluginName("netapp_api_info")].inventory_function


STRING_TABLE: Final = [
    ["system-name", "aspnetapp09"],
    ["system-id", "0536876124"],
    ["system-model", "FAS8040"],
    ["system-machine-type", "FAS8040"],
    ["vendor-id", "NetApp"],
    ["system-serial-number", "701414000905"],
    ["partner-system-id", "0536876447"],
    ["partner-system-name", "aspnetapp08"],
    ["system-revision", "A3"],
    ["backplane-part-number", "111-01459"],
    ["backplane-revision", "D0"],
    ["backplane-serial-number", "021351001008"],
    ["controller-address", "A"],
    ["board-speed", "2094"],
    ["board-type", "System Board XX"],
    ["cpu-part-number", "111-01209"],
    ["cpu-revision", "A3"],
    ["cpu-serial-number", "021404010722"],
    ["cpu-firmware-release", "9.3"],
    ["number-of-processors", "8"],
    ["memory-size", "32768"],
    ["cpu-processor-type", "Intel(R) Xeon(R) CPU E5-2658 @ 2.10GHz"],
    ["cpu-processor-id", "0x206d7"],
    ["cpu-microcode-version", "1808"],
    ["maximum-aggregate-size", "356241767399424"],
    ["maximum-flexible-volume-size", "109951162777600"],
    ["maximum-flexible-volume-count", "500"],
    ["supports-raid-array", "true"],
    ["prod-type", "FAS"],
    ["version", "NetApp Release 8.2.5P1 7-Mode: Thu Dec 21 21:09:11 PST 2017"],
    ["is-clustered", "false"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> StringTable:
    # make this apply the parse function once there is one.
    return STRING_TABLE


def test_inventory_solaris_addresses(section: StringTable, inventory_netapp_api_info) -> None:
    assert list(inventory_netapp_api_info(section)) == [
        Attributes(
            path=["hardware", "chassis"],
            inventory_attributes={
                "serial": "021351001008",
            },
        ),
        Attributes(
            path=["hardware", "cpu"],
            inventory_attributes={
                "cores": "8",
                "model": "Intel(R) Xeon(R) CPU E5-2658 @ 2.10GHz",
            },
        ),
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "model": "FAS8040",
                "product": "FAS8040",
                "serial": "701414000905",
                "id": "0536876124",
            },
        ),
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "vendor": "NetApp",
            },
        ),
    ]
