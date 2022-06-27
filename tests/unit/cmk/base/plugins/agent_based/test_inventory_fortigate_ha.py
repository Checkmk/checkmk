#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_fortigate_ha import (
    inventory_fortigate_ha,
    parse_fortigate_ha,
)

from .utils_inventory import sort_inventory_result

SECTION = {
    "mode": "activePassive",
    "group_id": "11",
    "prio": "128",
    "sched": "roundRobin",
    "group_name": "SZAG-DE-SAR-FF",
}


def test_parse_fortigate_ha() -> None:
    assert (
        parse_fortigate_ha(
            [
                [
                    "3",
                    "11",
                    "128",
                    "4",
                    "SZAG-DE-SAR-FF",
                ]
            ]
        )
        == SECTION
    )


def test_inventory_fortigate_ha() -> None:
    assert sort_inventory_result(inventory_fortigate_ha(SECTION)) == sort_inventory_result(
        [
            Attributes(
                path=["software", "applications", "fortinet", "fortigate_high_availability"],
                inventory_attributes={
                    "Mode": "activePassive",
                    "Priority": "128",
                    "Schedule": "roundRobin",
                    "Group ID": "11",
                    "Group Name": "SZAG-DE-SAR-FF",
                },
            ),
        ]
    )
