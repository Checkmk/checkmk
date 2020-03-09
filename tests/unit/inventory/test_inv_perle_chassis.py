#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]


@pytest.mark.parametrize(
    'info, inventory_data',
    [([["MODEL", "SERIAL", "BOOTLOADER", "FW", "_ALARMS", "_DIAGSTATE", "_TEMP_STR"]], {
        "serial": "SERIAL",
        "model": "MODEL",
        "bootloader": "BOOTLOADER",
        "firmware": "FW"
    })])
def test_inv_perle_chassis(inventory_plugin_manager, info, inventory_data):
    inv_plugin = inventory_plugin_manager.get_inventory_plugin('perle_chassis')
    inventory_tree_data, status_tree_data = inv_plugin.run_inventory(info)

    assert status_tree_data == {}

    path = "hardware.chassis."
    assert path in inventory_tree_data

    node_inventory_data = inventory_tree_data[path]
    assert sorted(node_inventory_data.items()) == sorted(inventory_data.items())
