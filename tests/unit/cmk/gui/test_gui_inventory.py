#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.inventory
from cmk.utils.structured_data import StructuredDataNode


@pytest.mark.parametrize("raw_path, expected_path", [
    ("", ([], None)),
    (".", ([], None)),
    (".hardware.", (["hardware"], None)),
    (".hardware.cpu.", (["hardware", "cpu"], None)),
    (".hardware.cpu.model", (["hardware", "cpu"], ["model"])),
    (".software.packages:", (["software", "packages"], [])),
    (".software.packages:17.name", (["software", "packages", "17"], ["name"])),
])
def test_parse_tree_path(raw_path, expected_path):
    assert cmk.gui.inventory.parse_tree_path(raw_path) == expected_path


@pytest.mark.parametrize("hostname, row, expected_tree", [
    (None, {}, StructuredDataNode.deserialize({"loaded": "tree"})),
    ("hostname", {}, StructuredDataNode.deserialize({"loaded": "tree"})),
    ("hostname", {
        "host_structured_status": b""
    }, StructuredDataNode.deserialize({"loaded": "tree"})),
    ("hostname", {
        "host_structured_status": b"{'deserialized': 'tree'}"
    }, StructuredDataNode.deserialize({"deserialized": "tree"})),
])
def test__load_status_data_tree(monkeypatch, hostname, row, expected_tree):
    monkeypatch.setattr(cmk.gui.inventory, "_load_structured_data_tree",
                        lambda t, hostname: StructuredDataNode.deserialize({"loaded": "tree"}))
    status_data_tree = cmk.gui.inventory._load_status_data_tree(hostname, row)
    assert status_data_tree is not None
    assert status_data_tree.is_equal(expected_tree)


_InvTree = StructuredDataNode.deserialize({"inv": "node"})
_StatusDataTree = StructuredDataNode.deserialize({"status": "node"})
_MergedTree = StructuredDataNode.deserialize({"inv": "node", "status": "node"})


@pytest.mark.parametrize("inventory_tree, status_data_tree, expected_tree", [
    (_InvTree, None, _InvTree),
    (None, _StatusDataTree, _StatusDataTree),
    (_InvTree, _StatusDataTree, _MergedTree),
])
def test__merge_inventory_and_status_data_tree(inventory_tree, status_data_tree, expected_tree):
    merged_tree = cmk.gui.inventory._merge_inventory_and_status_data_tree(
        inventory_tree,
        status_data_tree,
    )
    assert merged_tree is not None
    assert merged_tree.is_equal(expected_tree)


def test__merge_inventory_and_status_data_tree_both_None():
    merged_tree = cmk.gui.inventory._merge_inventory_and_status_data_tree(None, None)
    assert merged_tree is None
