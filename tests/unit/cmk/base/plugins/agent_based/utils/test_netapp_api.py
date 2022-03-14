#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.utils.netapp_api import parse_netapp_api_multiple_instances

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                [
                    "interface e0a",
                    "mediatype auto-1000t-fd-up",
                    "flowcontrol full",
                    "mtusize 9000",
                    "ipspace-name default-ipspace",
                    "mac-address 01:b0:89:22:df:01",
                ],
                ["interface"],
            ],
            {
                "e0a": [
                    {
                        "interface": "e0a",
                        "mediatype": "auto-1000t-fd-up",
                        "flowcontrol": "full",
                        "mtusize": "9000",
                        "ipspace-name": "default-ipspace",
                        "mac-address": "01:b0:89:22:df:01",
                    }
                ]
            },
        )
    ],
)
def test_get_filesystem_levels(info, expected_result):
    result = parse_netapp_api_multiple_instances(info)
    assert result == expected_result
