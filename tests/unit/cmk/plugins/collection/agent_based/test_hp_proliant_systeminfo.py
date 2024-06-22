#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.plugins.collection.agent_based.hp_proliant_systeminfo as hps
from cmk.agent_based.v2 import Attributes


@pytest.fixture(name="section", scope="module")
def _get_section() -> hps._Serial:
    section = hps.parse_hp_proliant_systeminfo([["serial-number"]])
    assert section
    return section


def test_inventory_hp_proliant_systeminfo(section: hps._Serial) -> None:
    assert list(hps.inventory_hp_proliant_systeminfo(section)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "serial": "serial-number",
            },
        )
    ]
