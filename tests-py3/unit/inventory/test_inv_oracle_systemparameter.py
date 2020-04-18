#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]


@pytest.mark.parametrize('info, inventory_data, status_data',
                         [(
                             [["", "", ""]],
                             {},
                             {},
                         ),
                          ([['XE', 'lock_name_space', '', 'TRUE']], {
                              'sid': 'XE',
                              'isdefault': 'TRUE',
                              'name': 'lock_name_space',
                              'value': ''
                          }, {}),
                          ([['XE', 'TRUE'], ["XI", 'init', '123', 'TRUE']], {
                              'sid': 'XI',
                              'isdefault': 'TRUE',
                              'name': 'init',
                              'value': '123'
                          }, {})])
def test_inv_oracle_systemparameter(inventory_plugin_manager, check_manager, info, inventory_data,
                                    status_data):
    inv_plugin = inventory_plugin_manager.get_inventory_plugin('oracle_systemparameter')
    inventory_tree_data, _ = inv_plugin.run_inventory(info)

    path = "software.applications.oracle.systemparameter:"
    assert path in inventory_tree_data

    node_inventory_data = inventory_tree_data[path]
    if inventory_data:
        assert sorted(node_inventory_data[0].items()) == sorted(inventory_data.items())
    else:
        assert node_inventory_data == []
