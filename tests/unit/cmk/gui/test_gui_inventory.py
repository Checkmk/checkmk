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
