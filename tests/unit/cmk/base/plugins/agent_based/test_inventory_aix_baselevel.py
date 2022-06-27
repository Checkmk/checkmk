#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import inventory_aix_baselevel as abl
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="section")
def _get_section() -> abl.Section:
    return abl.parse_aix_baselevel([["some version"]])


def test_inventory(section: abl.Section) -> None:
    assert list(abl.inventory_aix_baselevel(section)) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "version": "some version",
                "vendor": "IBM",
                "type": "aix",
                "name": "IBM AIX some version",
            },
        ),
    ]
