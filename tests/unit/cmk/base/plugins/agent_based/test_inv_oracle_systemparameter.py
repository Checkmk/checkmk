#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import InventoryPluginName
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
def test_inv_oracle_systemparameter(fix_register, info, expected):
    plugin = fix_register.inventory_plugins[InventoryPluginName('oracle_systemparameter')]
    assert list(plugin.inventory_function(info)) == expected
