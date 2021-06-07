#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.inventory import parse_tree_path, _parse_visible_raw_inventory_path


@pytest.mark.parametrize("raw_path, expected_path", [
    ("", ([], None)),
    (".", ([], None)),
    (".hardware.", (["hardware"], None)),
    (".hardware.cpu.", (["hardware", "cpu"], None)),
    (".hardware.cpu.model", (["hardware", "cpu"], ["model"])),
    (".software.packages:", (["software", "packages"], [])),
    (".software.packages:17.name", (["software", "packages", 17], ["name"])),
])
def test_parse_tree_path(raw_path, expected_path):
    assert parse_tree_path(raw_path) == expected_path


@pytest.mark.parametrize("raw_path, expected_path", [
    ("", []),
    ("path.to.node_1", ["path", "to", "node_1"]),
])
def test__parse_visible_tree_path(raw_path, expected_path):
    assert _parse_visible_raw_inventory_path(raw_path) == expected_path
