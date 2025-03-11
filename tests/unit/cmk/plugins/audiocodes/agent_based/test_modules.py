#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import StringTable, TableRow
from cmk.plugins.audiocodes.agent_based.modules import (
    inventory_audiocodes_modules,
    parse_audiocodes_modules,
)

STRING_TABLE = [
    [],
    [
        ["295", "0", "6", "", ""],
        [
            "280",
            "13045759",
            "3",
            "7.20A.258.459",
            "\n\nKey features:\nBoard Type: Mediant 4000B",
        ],
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                TableRow(
                    path=["hardware", "components", "modules"],
                    key_columns={"type": "acMediant4000MPModule"},
                    inventory_columns={
                        "serial": "0",
                        "ha_status": "Not applicable",
                        "software_version": "",
                        "license_key_list": "",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["hardware", "components", "modules"],
                    key_columns={"type": "acMediant4000CPUmodule"},
                    inventory_columns={
                        "serial": "13045759",
                        "ha_status": "Redundant",
                        "software_version": "7.20A.258.459",
                        "license_key_list": "\n\nKey features:\nBoard Type: Mediant 4000B",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_system_information(
    string_table: Sequence[StringTable], expected_result: Sequence[TableRow]
) -> None:
    section = parse_audiocodes_modules(string_table)
    assert section is not None
    assert list(inventory_audiocodes_modules(section)) == expected_result
