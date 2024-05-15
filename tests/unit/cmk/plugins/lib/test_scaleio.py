#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.plugins.lib.scaleio import parse_scaleio


@pytest.mark.parametrize(
    "string_table, scaleio_section_name, parsed_section",
    [
        pytest.param(
            [
                ["aardvark", "b"],
                ["STORAGE_POOL", "4e9a44c700000000:"],
                ["ID", "4e9a44c700000000"],
                ["NAME", "pool01"],
                ["STORAGE_POOL", "BANANA"],
                ["ID", "BANANA"],
                ["NAME", "pool02"],
            ],
            "STORAGE_POOL",
            {
                "4e9a44c700000000": {
                    "ID": ["4e9a44c700000000"],
                    "NAME": ["pool01"],
                },
                "BANANA": {
                    "ID": ["BANANA"],
                    "NAME": ["pool02"],
                },
            },
            id="If the storage section is present in the string_table, a mapping with the storage ID as the item and with the storage info as the value is returned",
        ),
        pytest.param(
            [
                ["VOLUME", "4e9a44c700000000:"],
                ["ID", "4e9a44c700000000"],
                ["NAME", "pool01"],
            ],
            "STORAGE_POOL",
            {},
            id="If the storage section is not present in the info, an empty mapping is returned",
        ),
    ],
)
def test_parse_scaleio(
    string_table: StringTable,
    scaleio_section_name: str,
    parsed_section: Mapping[str, Mapping[str, Sequence[str]]],
) -> None:
    assert parse_scaleio(string_table, scaleio_section_name) == parsed_section
