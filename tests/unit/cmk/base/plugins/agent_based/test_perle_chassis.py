#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.perle_chassis as pc
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="section", scope="module")
def _get_section() -> pc._Section:
    section = pc.parse_perle_chassis(
        [
            [
                "MCR1900",
                "103-001715T10033",
                "0.0",
                "1.0G6",
                "0",
                "0",
                "23",
            ]
        ]
    )
    assert section
    return section


def test_inventory_perle_chassis(section: pc._Section) -> None:
    assert list(pc.inventory_perle_chassis(section)) == [
        Attributes(
            path=["hardware", "chassis"],
            inventory_attributes={
                "serial": "103-001715T10033",
                "model": "MCR1900",
                "bootloader": "0.0",
                "firmware": "1.0G6",
            },
        ),
    ]
