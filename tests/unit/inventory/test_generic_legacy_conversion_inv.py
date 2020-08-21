#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.api.agent_based.type_defs import InventoryPlugin
from cmk.base.api.agent_based.inventory_classes import Attributes

import cmk.base.api.agent_based.register as agent_based_register

import cmk.base.check_api as check_api
import cmk.base.inventory_plugins as inventory_plugins
import cmk.base.inventory as inventory

pytestmark = pytest.mark.checks


@pytest.fixture(scope="module", name="inv_info")
def _get_inv_info():
    inventory_plugins.load_plugins(
        check_api.get_check_api_context,
        inventory.get_inventory_context,
    )
    assert len(inventory_plugins.inv_info) > 100  # sanity check
    return inventory_plugins.inv_info.copy()


def test_create_section_plugin_from_legacy(inv_info):
    for inv_info_dict in inv_info.values():
        assert 'snmp_info' not in inv_info_dict


def test_migrated_inventory_plugin(inv_info):  # pylint: disable=unused-argument
    # pick a plugin, any plugin
    plugin = agent_based_register.get_inventory_plugin(InventoryPluginName("aix_baselevel"))
    assert plugin is not None

    # think of a version, and remember it:
    result = list(plugin.inventory_function([["42.23"]]))

    assert len(result) == 1

    attr = result[0]
    assert isinstance(attr, Attributes)
    assert attr.path == ["software", "os"]
    assert attr.status_attributes == {}
    assert attr.inventory_attributes == {
        "version": "42.23",  # abracadabra! Is this your version?
        "vendor": "IBM",
        "type": "aix",
        "name": "IBM AIX 42.23"
    }
