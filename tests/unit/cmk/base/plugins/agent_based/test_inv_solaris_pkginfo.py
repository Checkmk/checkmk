#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib import set_timezone  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
from cmk.base.api.agent_based import register
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow

INFO = [
    ['PKGINST', '  SUNWzoneu'],  # PKGINST
    ['NAME', '  Solaris Zones (Usr)'],
    ['CATEGORY', '  system'],
    ['ARCH', '  i386'],
    ['VERSION', '  11.11,REV=2009.11.11'],
    ['BASEDIR', '  /'],
    ['VENDOR', '  Oracle Corporation'],
    ['DESC', '  Solaris Zones Configuration and Administration'],
    ['INSTDATE', '  Aug 20 2018 13', '11'],
    ['HOTLINE', '  Please contact your local service provider'],
    ['STATUS', '  completely installed'],
    ['PKGINST', '  SUNWzyd'],  # PKGINST
    ['NAME', '  ZyDAS ZD1211 USB 802.11b/g Wireless Driver'],
    ['CATEGORY', '  system'],
    ['ARCH', '  i386'],
    ['VERSION', '  11.11,REV=2009.11.11'],
    ['BASEDIR', '  /'],
    ['VENDOR', '  Oracle Corporation'],
    ['DESC', '  ZyDAS ZD1211 USB 802.11b/g Wireless Driver'],
    ['INSTDATE', '  Aug 20 2018 13', '11'],
    ['HOTLINE', '  Please contact your local service provider'],
    ['STATUS', '  completely installed'],
]

RESULT = [
    TableRow(
        path=['software', 'packages'],
        key_columns={
            'name': '  SUNWzoneu -   Solaris Zones (Usr)',
            'package_type': 'system',
            'arch': 'i386',
            'version': '11.11,REV=2009.11.11',
            'vendor': 'Oracle Corporation',
            'summary': 'Solaris Zones Configuration and Administration',
            'install_date': 1534763460
        },
        inventory_columns={},
        status_columns={},
    ),
    TableRow(
        path=['software', 'packages'],
        key_columns={
            'name': '  SUNWzyd -   ZyDAS ZD1211 USB 802.11b/g Wireless Driver',
            'package_type': 'system',
            'arch': 'i386',
            'version': '11.11,REV=2009.11.11',
            'vendor': 'Oracle Corporation',
            'summary': 'ZyDAS ZD1211 USB 802.11b/g Wireless Driver',
            'install_date': 1534763460
        },
        inventory_columns={},
        status_columns={},
    ),
]


@pytest.mark.usefixtures("config_load_all_inventory_plugins")
def test_inv_solaris_pkginfo() -> None:
    plugin = register.get_inventory_plugin(InventoryPluginName('solaris_pkginfo'))
    assert plugin
    with set_timezone("ETC-2"):
        result = list(plugin.inventory_function(INFO))
    assert result == RESULT
