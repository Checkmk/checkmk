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
@pytest.mark.parametrize(
    'info, params, inventory_data',
    [
        (
            [],
            {},
            [],
        ),
        (
            [
                ['abi.vsyscall32', '=', '1'],
            ],
            {},
            [],
        ),
        (
            [],
            {
                'include_patterns': ['.*'],
            },
            [],
        ),
        (
            [
                ['abi.vsyscall32', '=', '1'],
                [
                    'dev.cdrom.info', '=', 'CD-ROM', 'information,', 'Id:', 'cdrom.c', '3.20',
                    '2003/12/17'
                ],
                ['dev.cdrom.info', '='],
                ['dev.cdrom.info', '=', 'drive', 'name:'],
                ['dev.cdrom.info', '=', 'drive', 'speed:'],
                ['dev.cdrom.info', '=', 'drive', '#', 'of', 'slots:'],
                ['dev.cdrom.info', '='],
                ['dev.cdrom.info', '='],
                ['dev.hpet.max-user-freq', '=', '64'],
                ['kernel.hotplug', '='],
                ['kernel.hung_task_check_count', '=', '4194304'],
            ],
            {
                'include_patterns': ['.*'],
                'exclude_patterns': ['kernel.hotplug'],
            },
            [
                TableRow(
                    path=['software', 'kernel_config'],
                    key_columns={
                        'parameter': 'abi.vsyscall32',
                        'value': '1',
                    },
                ),
                TableRow(
                    path=['software', 'kernel_config'],
                    key_columns={
                        'parameter': 'dev.cdrom.info',
                        'value': 'CD-ROM information, Id: cdrom.c 3.20 2003/12/17',
                    },
                ),
                TableRow(
                    path=['software', 'kernel_config'],
                    key_columns={
                        'parameter': 'dev.cdrom.info',
                        'value': 'drive name:',
                    },
                ),
                TableRow(
                    path=['software', 'kernel_config'],
                    key_columns={
                        'parameter': 'dev.cdrom.info',
                        'value': 'drive speed:',
                    },
                ),
                TableRow(
                    path=['software', 'kernel_config'],
                    key_columns={
                        'parameter': 'dev.cdrom.info',
                        'value': 'drive # of slots:',
                    },
                ),
                TableRow(
                    path=['software', 'kernel_config'],
                    key_columns={
                        'parameter': 'dev.hpet.max-user-freq',
                        'value': '64',
                    },
                ),
                TableRow(
                    path=['software', 'kernel_config'],
                    key_columns={
                        'parameter': 'kernel.hung_task_check_count',
                        'value': '4194304',
                    },
                ),
            ],
        ),
        (
            [
                ['abi.vsyscall32', '=', '1'],
                [
                    'dev.cdrom.info', '=', 'CD-ROM', 'information,', 'Id:', 'cdrom.c', '3.20',
                    '2003/12/17'
                ],
                ['dev.cdrom.info', '='],
                ['dev.cdrom.info', '=', 'drive', 'name:'],
                ['dev.cdrom.info', '=', 'drive', 'speed:'],
                ['dev.cdrom.info', '=', 'drive', '#', 'of', 'slots:'],
                ['dev.cdrom.info', '='],
                ['dev.cdrom.info', '='],
                ['dev.hpet.max-user-freq', '=', '64'],
                ['kernel.hotplug', '='],
                ['kernel.hung_task_check_count', '=', '4194304'],
            ],
            {
                'include_patterns': ['.*'],
                'exclude_patterns': ['.*'],
            },
            [],
        ),
    ],
)
def test_inv_oracle_systemparameter(info, params, inventory_data):
    plugin = agent_based_register.get_inventory_plugin(InventoryPluginName('lnx_sysctl'))
    assert plugin
    assert list(plugin.inventory_function(params, info)) == inventory_data
