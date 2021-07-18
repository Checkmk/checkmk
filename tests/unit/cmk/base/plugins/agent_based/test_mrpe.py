#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import mrpe

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, expected_parse_result", [
    (
        [
            ['Desc1', '0', 'This', 'is', 'old', 'style'],
            ['(test_plugin)', 'Desc2', '0', 'This', 'is', 'a', 'bit', 'newer'],
        ],
        {
            'Desc1': [mrpe.PluginData(
                None,
                0,
                ['This is old style'],
            )],
            'Desc2': [mrpe.PluginData(
                "test_plugin",
                0,
                ['This is a bit newer'],
            )],
        },
    ),
])
def test_mrpe_parse(monkeypatch, info, expected_parse_result):
    assert mrpe.parse_mrpe(info) == expected_parse_result
