#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow


@pytest.mark.usefixtures("config_load_all_inventory_plugins")
@pytest.mark.parametrize('info, inventory_data', [
    (
        [
            ['|device|/sys/devices/pci0000:00/0000:00:1d.4/0000:3b:00.0/nvme/nvme0/nvme0n1|'],
            ['|size|1000215216|'],
            ['|uuid|ace42e00-955b-21fd-2ee4-ac0000000001|'],
            ['|device/address|0000:3b:00.0|'],
            ['|device/firmware_rev|80002111|'],
            ['|device/model|PC601 NVMe SK hynix 512GB               |'],
            ['|device/serial|AJ98N635810808T29   |'],
        ],
        [
            TableRow(
                path=['hardware', 'storage', 'disks'],
                key_columns={
                    'firmware': '80002111',
                    'fsnode': '/sys/devices/pci0000:00/0000:00:1d.4/0000:3b:00.0/nvme/nvme0/nvme0n1',
                    'product': 'PC601 NVMe SK hynix 512GB',
                    'serial': 'AJ98N635810808T29',
                    'signature': 'ace42e00-955b-21fd-2ee4-ac0000000001',
                    'size': 512110190592,
                },
            )
        ],
    ),
])
def test_inv_lnx_block_devices(info, inventory_data):
    plugin = agent_based_register.get_inventory_plugin(InventoryPluginName('lnx_block_devices'))
    assert plugin
    assert list(plugin.inventory_function(info)) == inventory_data
