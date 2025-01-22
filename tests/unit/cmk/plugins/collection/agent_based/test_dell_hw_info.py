#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import UTC

from cmk.agent_based.v2 import (
    Attributes,
)
from cmk.plugins.collection.agent_based.dell_hw_info import (
    _inventory_testable,
    parse_dell_hw_info,
    Section,
)

_STRING_TABLE = [
    [
        "7.10.50.10",
        "FGS8YY3",
        "33666641643",
        "03/03/2023",
        "1.10.2",
        "Dell Inc.",
        "PERC H355 Front (Embedded)",
        "52.21.0-4606",
    ]
]


def _parsed_section() -> Section:
    section = parse_dell_hw_info(_STRING_TABLE)
    assert section
    return section


def test_inventory_testable() -> None:
    assert list(_inventory_testable(_parsed_section(), UTC)) == [
        Attributes(
            path=["software", "firmware"],
            inventory_attributes={"version": "7.10.50.10"},
            status_attributes={},
        ),
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={"serial": "FGS8YY3", "expresscode": "33666641643"},
            status_attributes={},
        ),
        Attributes(
            path=["software", "bios"],
            inventory_attributes={"version": "1.10.2", "vendor": "Dell Inc.", "date": 1677801600.0},
            status_attributes={},
        ),
        Attributes(
            path=["hardware", "storage", "controller"],
            inventory_attributes={"version": "52.21.0-4606", "name": "PERC H355 Front (Embedded)"},
            status_attributes={},
        ),
    ]
