#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import time

from cmk.base.plugins.agent_based import mrpe
from cmk.base.plugins.agent_based.utils import cache_helper

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, expected_parse_result", [
    (
        [
            ['Desc1', '0', 'This', 'is', 'old', 'style'],
            ['(test_plugin)', 'Desc2', '0', 'This', 'is', 'a', 'bit', 'newer'],
            [
                'cached(1626596950,300)', '(test_plugin)', 'Desc3', '0', 'This', 'is', 'even',
                'newer'
            ],
        ],
        {
            'Desc1': [mrpe.PluginData(
                None,
                0,
                ['This is old style'],
                None,
            )],
            'Desc2': [mrpe.PluginData(
                "test_plugin",
                0,
                ['This is a bit newer'],
                None,
            )],
            'Desc3': [
                mrpe.PluginData(
                    "test_plugin",
                    0,
                    ["This is even newer"],
                    cache_helper.CacheInfo(age=750.0, cache_interval=300.0),
                )
            ],
        },
    ),
])
def test_mrpe_parse(monkeypatch, info, expected_parse_result):
    monkeypatch.setattr(time, "time", lambda: 1626597700)
    assert mrpe.parse_mrpe(info) == expected_parse_result
