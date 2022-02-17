#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

from .utils_inventory import sort_inventory_result

INFO = [["MODEL", "SERIAL", "BOOTLOADER", "FW", "_ALARMS", "_DIAGSTATE", "_TEMP_STR"]]

EXPECTED = [
    Attributes(
        path=["hardware", "chassis"],
        inventory_attributes={
            "serial": "SERIAL",
            "model": "MODEL",
            "bootloader": "BOOTLOADER",
            "firmware": "FW",
        },
    ),
]


def test_inv_perle_chassis(fix_register):
    plugin = fix_register.inventory_plugins[InventoryPluginName("perle_chassis")]
    assert sort_inventory_result(plugin.inventory_function(INFO)) == sort_inventory_result(EXPECTED)
