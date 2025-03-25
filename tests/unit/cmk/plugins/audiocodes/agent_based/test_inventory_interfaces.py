#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable, TableRow
from cmk.plugins.audiocodes.agent_based.interfaces import (
    inventory_audiocodes_sip_interfaces,
    parse_audiocodes_interfaces,
)

STRING_TABLE = [
    [
        [
            "0",
            "1",
            "0",
            "0",
            ".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.22.1.11.1",
            "2",
            "0",
            "5060",
            "0",
            "4294967295",
            "OXE intern",
        ],
        [
            "1",
            "1",
            "0",
            "0",
            ".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.22.1.11.2",
            "2",
            "0",
            "5060",
            "0",
            "4294967295",
            "OXE extern",
        ],
    ],
    [
        [
            "1",
            "1",
            "5",
            "10",
            "192.168.0.1",
            "24",
            "192.168.0.2",
            "1",
            "LAN_TK01",
            "192.168.0.4",
            "192.168.0.5",
            ".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.24.1.5.0",
            ".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.26.1.7.0",
        ],
        [
            "2",
            "1",
            "5",
            "10",
            "192.168.0.3",
            "24",
            "192.168.0.2",
            "1",
            "LAN_TK02",
            "192.168.0.4",
            "192.168.0.5",
            ".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.24.1.5.0",
            ".1.3.6.1.4.1.5003.9.10.10.1.3.1.30.26.1.7.0",
        ],
    ],
    [
        ["0", "1", "1", "LAN"],
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param([], {}),
        pytest.param(
            STRING_TABLE,
            {
                "OXE intern": TableRow(
                    path=["networking", "sip_interfaces"],
                    key_columns={"index": "0", "name": "OXE intern"},
                    inventory_columns={
                        "application_type": "sbc",
                        "sys_interface": "LAN_TK01",
                        "device": "LAN",
                        "tcp_port": 5060,
                        "gateway": "192.168.0.2",
                    },
                    status_columns={},
                ),
                "OXE extern": TableRow(
                    path=["networking", "sip_interfaces"],
                    key_columns={"index": "1", "name": "OXE extern"},
                    inventory_columns={
                        "application_type": "sbc",
                        "sys_interface": "LAN_TK02",
                        "device": "LAN",
                        "tcp_port": 5060,
                        "gateway": "192.168.0.2",
                    },
                    status_columns={},
                ),
            },
        ),
    ],
)
def test_inventory_interfaces(
    string_table: Sequence[StringTable], expected_result: Mapping[str, TableRow]
) -> None:
    table_rows = {}

    for table_row in inventory_audiocodes_sip_interfaces(parse_audiocodes_interfaces(string_table)):
        assert isinstance(table_row, TableRow)
        table_rows[table_row.key_columns["name"]] = table_row

    assert table_rows == expected_result
