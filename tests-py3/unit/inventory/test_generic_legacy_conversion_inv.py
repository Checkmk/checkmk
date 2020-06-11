#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest  # type: ignore[import]

import cmk.base.check_api as check_api
import cmk.base.inventory_plugins as inventory_plugins

pytestmark = pytest.mark.checks


@pytest.fixture(scope="module", name="inv_info")
def _get_inv_info():
    inventory_plugins.load_plugins(check_api.get_check_api_context, lambda: {})
    assert len(inventory_plugins.inv_info) > 100  # sanity check
    return inventory_plugins.inv_info.copy()


def test_create_section_plugin_from_legacy(inv_info):
    for inv_info_dict in inv_info.values():
        assert 'snmp_info' not in inv_info_dict
