#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final

import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.windows.agent_based.inventory_win_bios import inventory_win_bios, parse_win_bios

OUTPUT: Final = """Manufacturer       : innotek GmbH
Name               : Default System BIOS
BIOSVersion        : {VBOX   - 1}
ListOfLanguages    :
PrimaryBIOS        : True
ReleaseDate        : 20061201000000.000000+000
SMBIOSBIOSVersion  : VirtualBox
SMBIOSMajorVersion : 2
SMBIOSMinorVersion : 5
"""


@pytest.fixture(name="section")
def _get_section() -> Mapping[str, str | int]:
    return parse_win_bios([line.split(":") for line in OUTPUT.split("\n")])


def test_inventory_win_bios(section: Mapping[str, str | int]) -> None:
    assert list(inventory_win_bios({**section, "date": 0})) == [  # aviod TZ issues in C
        Attributes(
            path=["software", "bios"],
            inventory_attributes={
                "date": 0,
                "model": "Default System BIOS",
                "vendor": "innotek GmbH",
                "version": "VirtualBox 2.5",
            },
        )
    ]
