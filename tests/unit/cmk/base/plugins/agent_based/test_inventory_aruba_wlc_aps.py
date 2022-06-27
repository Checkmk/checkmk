#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.aruba_wlc_aps import inventory_aruba_wlc_aps, parse_aruba_wlc_aps

from .utils_inventory import sort_inventory_result


@pytest.mark.parametrize(
    "raw_section, expected_result",
    [
        ([], []),
        (
            [
                ["name 1", "1", "1", "1.2.3.4", "group 1", "1", "serial 1", "sys location 1"],
                ["name 2", "2", "2", "5.6.7.8", "group 2", "foo", "serial 2", "sys location 2"],
            ],
            [
                TableRow(
                    path=["networking", "wlan", "controller", "accesspoints"],
                    key_columns={
                        "name": "name 1",
                    },
                    inventory_columns={
                        "ip_addr": "1.2.3.4",
                        "group": "group 1",
                        "model": "a50",
                        "serial": "serial 1",
                        "sys_location": "sys location 1",
                    },
                ),
                TableRow(
                    path=["networking", "wlan", "controller", "accesspoints"],
                    key_columns={
                        "name": "name 2",
                    },
                    inventory_columns={
                        "ip_addr": "5.6.7.8",
                        "group": "group 2",
                        "model": "unknown",
                        "serial": "serial 2",
                        "sys_location": "sys location 2",
                    },
                ),
            ],
        ),
    ],
)
def test_inventory_aruba_wlc_aps(raw_section, expected_result) -> None:
    assert sort_inventory_result(
        inventory_aruba_wlc_aps(parse_aruba_wlc_aps(raw_section))
    ) == sort_inventory_result(expected_result)
