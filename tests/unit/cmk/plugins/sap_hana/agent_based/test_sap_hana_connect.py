#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.sap_hana.agent_based.sap_hana_connect import (
    check_sap_hana_connect,
    discover_sap_hana_connect,
    parse_sap_hana_connect,
)

INFO_0 = [
    ["[[YYY 11]]"],
    [
        "ODBC Driver test.",
        "",
        "Connect string: 'SERVERNODE=lllllllllllll:30003,UID=MOOOOOO,PWD=xxx,'.",
        "retcode:\t 0",
        "outString(58):\tSERVERNODE={lllllllllllll:30003},UID=MOOOOOO,PWD=xxx,",
        "Driver version 02.12.0025 (2022-05-06).",
        "Select now(): 2022-11-28 10:03:08.095000000 (29)",
    ],
]

INFO_1 = [
    ["[[YYY 11]]"],
    [
        "ODBC Driver test.",
        "",
        "Connect string: 'SERVERNODE=lllllllllllll:30003,SERVERDB=BAS,UID=MOOOOOO,PWD=xxx,'.",
        "retcode:\t 0",
        "outString(58):\tSERVERNODE={lllllllllllll:30003},SERVERDB=BAS,UID=MOOOOOO,PWD=xxx,",
        "Driver version 02.12.0025 (2022-05-06).",
        "Select now(): 2022-11-28 10:03:08.095000000 (29)",
    ],
]


@pytest.mark.parametrize("info", [INFO_0, INFO_1])
def test_sap_hana_connect_missing_serverdb(info: StringTable) -> None:
    assert parse_sap_hana_connect(info) == {
        "YYY 11": {
            "cmk_state": State.OK,
            "driver_version": "02.12.0025 (2022-05-06).",
            "message": "Worker: OK",
            "server_node": "lllllllllllll:30003",
            "timestamp": "2022-11-28 10:03:08",
        },
    }


STRING_TABLE = [
    ["[[H00 00]]"],
    ["retcode: 1"],
    ["[[H11 11]]"],
    [
        "ODBC Driver test.",
        "",
        "Connect string: 'SERVERNODE=Hana-host:3inst13,SERVERDB=BAS,UID=MyName,PWD=MyPass,'.",
        "retcode:         0",
        "outString(68):  SERVERNODE={Hana-host:3inst13},SERVERDB=BAS,UID=MyName,PWD=MyPass,",
        "Driver version SAP HDB 1.00 (2013-10-15).",
        "Select now(): 2013-11-12 15:44:55.272000000 (29)",
    ],
    ["[[H22 22]]"],
    [
        "ODBC Driver test.",
        "",
        "Connect string: 'SERVERNODE=Hana-host:3inst13,SERVERDB=BAS,UID=MyName,PWD=MyPass,'.",
        "retcode:         1",
        "outString(68):  SERVERNODE={Hana-host:3inst13},SERVERDB=BAS,UID=MyName,PWD=MyPass,",
        "Driver version SAP HDB 1.00 (2013-10-15).",
        "Select now(): 2013-11-12 15:44:55.272000000 (29)",
    ],
    ["[[H33 33]]"],
    [
        "ODBC Driver test.",
        "",
        "Connect string: 'SERVERNODE=Hana-host:3inst13,SERVERDB=BAS,UID=MyName,PWD=MyPass,'.",
        "retcode:         3",
        "outString(68):  SERVERNODE={Hana-host:3inst13},SERVERDB=BAS,UID=MyName,PWD=MyPass,",
        "Driver version SAP HDB 1.00 (2013-10-15).",
        "Select now(): 2013-11-12 15:44:55.272000000 (29)",
    ],
    ["[[H44 44]]"],
    ["Wrong Password", "Error connecting to ODBC Driver"],
]


def test_discover_sap_hana_connect() -> None:
    parsed = parse_sap_hana_connect(STRING_TABLE)
    result = list(discover_sap_hana_connect(parsed))
    assert sorted(result, key=lambda s: s.item or "") == [
        Service(item="H00 00"),
        Service(item="H11 11"),
        Service(item="H22 22"),
        Service(item="H33 33"),
        Service(item="H44 44"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "H00 00",
            [
                Result(
                    state=State.OK,
                    summary="Standby: OK",
                    details="ODBC Driver Version: not found, Server Node: not found, Timestamp: not found",
                )
            ],
        ),
        (
            "H11 11",
            [
                Result(
                    state=State.OK,
                    summary="Worker: OK",
                    details="ODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                )
            ],
        ),
        (
            "H22 22",
            [
                Result(
                    state=State.OK,
                    summary="Standby: OK",
                    details="ODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                )
            ],
        ),
        (
            "H33 33",
            [
                Result(
                    state=State.CRIT,
                    summary="No connect",
                    details="ODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                )
            ],
        ),
        (
            "H44 44",
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Wrong Password Error connecting to ODBC Driver",
                    details="ODBC Driver Version: not found, Server Node: not found, Timestamp: not found",
                )
            ],
        ),
    ],
)
def test_check_sap_hana_connect(item: str, expected_results: Sequence[Result]) -> None:
    parsed = parse_sap_hana_connect(STRING_TABLE)
    result = list(check_sap_hana_connect(item, parsed))
    assert result == expected_results
