#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List

import pytest

from cmk.base.api.agent_based.inventory_classes import TableRow
from cmk.base.api.agent_based.register.inventory_plugins_legacy import (
    _generate_table_rows,
    MockStructuredDataNode,
)


def test__generate_table_rows_list() -> None:
    local_status_data_tree = MockStructuredDataNode()
    local_inventory_tree = MockStructuredDataNode()

    def plugin_list():
        node = local_inventory_tree.get_list("level0_1.level1_list:")
        for a, b in [("l", "L1"), ("l", "L2")]:
            node.append({a: b})

    plugin_list()

    table_rows = list(_generate_table_rows(local_status_data_tree, local_inventory_tree))
    assert table_rows == [
        TableRow(
            path=["level0_1", "level1_list"],
            key_columns={"l": "L1"},
            inventory_columns={},
            status_columns={},
        ),
        TableRow(
            path=["level0_1", "level1_list"],
            key_columns={"l": "L2"},
            inventory_columns={},
            status_columns={},
        ),
    ]


def test__generate_table_rows_nested_list() -> None:
    # Now such (shipped) inventory plugins exists any more.
    local_status_data_tree = MockStructuredDataNode()
    local_inventory_tree = MockStructuredDataNode()

    def plugin_nested_list():
        node = local_inventory_tree.get_list("level0_2.level1_nested_list:")
        for index in range(10):
            array: Dict[str, List[Dict[str, str]]] = {"foo": []}
            for a, b in [("nl", "NL1"), ("nl", "NL2")]:
                array["foo"].append({a: "%s-%s" % (b, index)})
            node.append(array)

    plugin_nested_list()
    with pytest.raises(TypeError):
        list(_generate_table_rows(local_status_data_tree, local_inventory_tree))
