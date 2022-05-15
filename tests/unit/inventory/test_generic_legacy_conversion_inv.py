#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.api.agent_based.inventory_classes import Attributes

pytestmark = pytest.mark.checks


def test_no_new_legacy_tests():
    this_dir = Path(__file__).parent

    assert [p.name for p in this_dir.iterdir() if p.name != "__pycache__"] == [
        "test_generic_legacy_conversion_inv.py",
    ], (
        "Please do not put new tests in %s. They belong to the tests for agent_based plugins."
        % this_dir
    )


def test_create_section_plugin_from_legacy(fix_plugin_legacy):
    for inv_info_dict in fix_plugin_legacy.inv_info.values():
        assert "snmp_info" not in inv_info_dict


def test_migrated_inventory_plugin(fix_plugin_legacy, fix_register):
    # pick an automigrated plugin
    test_plugin_name = "perle_chassis"
    assert test_plugin_name in fix_plugin_legacy.inv_info

    plugin = fix_register.inventory_plugins.get(InventoryPluginName(test_plugin_name))
    assert plugin is not None

    # think of a model, and remember it:
    result = list(plugin.inventory_function([["42.23", "", "", "", "", "", ""]]))

    assert len(result) == 1

    attr = result[0]
    assert isinstance(attr, Attributes)
    assert attr.inventory_attributes["model"] == "42.23"  # abracadabra! Is this your model?
