#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]


@pytest.mark.parametrize(
    'info, params, inventory_data',
    [
        (
            [],
            {},
            None,
        ),
        (
            [
                ['abi.vsyscall32', '=', '1'],
            ],
            {},
            None,
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
                {
                    'parameter': 'abi.vsyscall32',
                    'value': '1',
                },
                {
                    'parameter': 'dev.cdrom.info',
                    'value': 'CD-ROM information, Id: cdrom.c 3.20 2003/12/17',
                },
                {
                    'parameter': 'dev.cdrom.info',
                    'value': 'drive name:',
                },
                {
                    'parameter': 'dev.cdrom.info',
                    'value': 'drive speed:',
                },
                {
                    'parameter': 'dev.cdrom.info',
                    'value': 'drive # of slots:',
                },
                {
                    'parameter': 'dev.hpet.max-user-freq',
                    'value': '64',
                },
                {
                    'parameter': 'kernel.hung_task_check_count',
                    'value': '4194304',
                },
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
def test_inv_oracle_systemparameter(inventory_plugin_manager, info, params, inventory_data):
    inv_plugin = inventory_plugin_manager.get_inventory_plugin('lnx_sysctl')
    inventory_tree_data, _ = inv_plugin.run_inventory(info, params)

    path = "software.kernel_config:"
    if inventory_data is None:
        assert path not in inventory_tree_data
    else:
        assert inventory_tree_data[path] == inventory_data
