#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based import inventory_aix_baselevel as abl


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
