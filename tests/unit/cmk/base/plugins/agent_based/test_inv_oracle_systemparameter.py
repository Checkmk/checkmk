#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow


@pytest.mark.parametrize('info, expected', [
    ([["", "", ""]], []),
    ([['XE', 'lock_name_space', '', 'TRUE']], [
        TableRow(
            path=['software', 'applications', 'oracle', 'systemparameter'],
            key_columns={
                'sid': 'XE',
                'name': 'lock_name_space',
                'value': '',
                'isdefault': 'TRUE',
            },
        )
    ]),
    ([['XE', 'TRUE'], ["XI", 'init', '123', 'TRUE']], [
        TableRow(
            path=['software', 'applications', 'oracle', 'systemparameter'],
            key_columns={
                'sid': 'XI',
                'name': 'init',
                'value': '123',
                'isdefault': 'TRUE',
            },
        ),
    ]),
])
@pytest.mark.usefixtures("config_load_all_inventory_plugins")
def test_inv_oracle_systemparameter(info, expected):
    plugin = agent_based_register.get_inventory_plugin(
        InventoryPluginName('oracle_systemparameter'))
    assert plugin
    assert list(plugin.inventory_function(info)) == expected
