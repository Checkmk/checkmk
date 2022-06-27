#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.lparstat_aix import (
    inventory_lparstat_aix,
    parse_lparstat_aix,
    Section,
)


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section:
    section = parse_lparstat_aix(
        [
            [
                "System",
                "configuration:",
                "type=Dedicated",
                "mode=Capped",
                "smt=4",
                "lcpu=4",
                "mem=16384MB",
            ],
            ["%user", "%sys", "%wait", "%idle"],
            ["-----", "-----", "------", "------"],
            ["0.1", "58.8", "0.0", "41.1"],
        ]
    )
    assert section is not None
    return section


def test_inventory_lparstat_aix(section: Section) -> None:
    assert list(inventory_lparstat_aix(section)) == [
        Attributes(
            path=["hardware", "cpu"],
            inventory_attributes={
                "sharing_mode": "Dedicated-Capped",
                "smt_threads": "4",
                "logical_cpus": "4",
            },
        ),
    ]
