#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

INFO = [["MODEL", "SERIAL", "BOOTLOADER", "FW", "_ALARMS", "_DIAGSTATE", "_TEMP_STR"]]

EXPECTED = [
    Attributes(
        path=['hardware', 'chassis'],
        inventory_attributes={
            "serial": "SERIAL",
            "model": "MODEL",
            "bootloader": "BOOTLOADER",
            "firmware": "FW",
        },
    ),
]


@pytest.mark.usefixtures("config_load_all_inventory_plugins")
def test_inv_perle_chassis():
    plugin = agent_based_register.get_inventory_plugin(InventoryPluginName('perle_chassis'))
    assert plugin
    assert list(plugin.inventory_function(INFO)) == EXPECTED
