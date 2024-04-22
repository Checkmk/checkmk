#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.base.plugins.agent_based.win_computersystemproduct as wcsp
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

# <<<win_computersystemproduct:sep(58):persist(1713282994)>>>
# IdentifyingNumber:
# Name: Standard PC (Q35 + ICH9, 2009)
# UUID: 28926C71-246D-4438-BD02-26F0E721FECD
# Vendor: QEMU

STRING_TABLE = [
    ["IdentifyingNumber", ""],
    ["Name", "Standard PC (Q35 + ICH9, 2009)"],
    ["UUID", "28926C71-246D-4438-BD02-26F0E721FECD"],
    ["Vendor", "QEMU"],
]


def test_inventory_win_computersystemproduct() -> None:
    assert list(
        wcsp.inventory_win_computersystemproduct(
            wcsp.parse_win_computersystemproduct(STRING_TABLE),
        )
    ) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "uuid": "28926C71-246D-4438-BD02-26F0E721FECD",
            },
        ),
    ]
