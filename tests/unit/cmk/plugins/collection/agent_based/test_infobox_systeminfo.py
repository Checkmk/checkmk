#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.plugins.collection.agent_based.infoblox_systeminfo as ibsi
from cmk.agent_based.v2 import Attributes


def _section() -> ibsi.Section:
    assert (
        section := ibsi.parse_infoblox_systeminfo(
            [
                [
                    "IB-VM-820",
                    "422cc26d1a7a6eec1b03bd16cc74cfe7",
                    "422cc26d1a7a6eec1b03bd16cc74cfe7",
                    "7.2.7",
                ]
            ]
        )
    ) is not None
    return section


def test_inventory_infoblox_systeminfo() -> None:
    assert list(ibsi.inventory_infoblox_systeminfo(_section())) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "model": "IB-VM-820",
                "hardware_id": "422cc26d1a7a6eec1b03bd16cc74cfe7",
                "serial": "422cc26d1a7a6eec1b03bd16cc74cfe7",
                "version": "7.2.7",
            },
        ),
    ]
