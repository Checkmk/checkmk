#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName
from cmk.base.item_state import MKCounterWrapped


@pytest.mark.parametrize("item, parsed", [
    (
        "file1234.txt",
        {
            "reftime": 1563288717,
            "files": {}
        },
    ),
])
def test_sap_hana_fileinfo(fix_register, item, parsed):
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo")]
    with pytest.raises(MKCounterWrapped) as e:
        list(plugin.check_function(item=item, params={}, section=parsed))

    assert e.value.args[0] == "Login into database failed."


@pytest.mark.parametrize("item, parsed", [
    (
        "file1234.txt",
        {
            "reftime": 1563288717,
            "files": {}
        },
    ),
])
def test_sap_hana_fileinfo_groups(fix_register, item, parsed):
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo_groups")]
    with pytest.raises(MKCounterWrapped) as e:
        list(plugin.check_function(item=item, params={}, section=parsed))

    assert e.value.args[0] == "Login into database failed."
