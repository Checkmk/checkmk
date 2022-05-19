#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from testlib import Check  # type: ignore[import]


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_netapp_api_qtree_quota_duplicate_item_names() -> None:
    check_plugin = Check("netapp_api_qtree_quota")

    string_table = [
        [
            "quota somequota",
            "disk-limit 83886080",
            "disk-used 60654012",
            "quota-type tree",
            "volume vol0",
        ],
        [
            "quota somequota",
            "disk-limit 83886080",
            "disk-used 4388",
            "quota-type user",
            "volume vol0",
        ],
    ]

    parsed_items = check_plugin.run_parse(string_table)
    assert parsed_items == {
        'somequota': {
            'disk-limit': '83886080',
            'disk-used': '60654012',
            'quota': 'somequota',
            'quota-type': 'tree',
            'volume': 'vol0',
        },
    }
