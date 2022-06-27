#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.win_computersystem as wcs
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="section", scope="module")
def _get_section() -> wcs._Section:
    return wcs.parse_win_computersystem(
        [
            ["Manufacturer", " FUJITSU"],
            ["Model", " PRIMERGY RX100 S7"],
            ["Name", "<WINDOWSHOST>"],
        ]
    )


def test_inventory_win_computersystem(section: wcs._Section) -> None:
    assert list(wcs.inventory_win_computersystem(section)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "manufacturer": "FUJITSU",
                "model": "PRIMERGY RX100 S7",
                "family": "<WINDOWSHOST>",
            },
        ),
    ]
