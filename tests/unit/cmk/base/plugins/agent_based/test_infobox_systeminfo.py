#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.infoblox_systeminfo as ibsi
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="section", scope="module")
def _get_section() -> ibsi.Section:
    return ibsi.parse_infoblox_systeminfo(
        [
            [
                "IB-VM-820",
                "422cc26d1a7a6eec1b03bd16cc74cfe7",
                "422cc26d1a7a6eec1b03bd16cc74cfe7",
                "7.2.7",
            ]
        ]
    )


def test_inventory_infoblox_systeminfo(section: ibsi.Section) -> None:
    assert list(ibsi.inventory_infoblox_systeminfo(section)) == [
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
