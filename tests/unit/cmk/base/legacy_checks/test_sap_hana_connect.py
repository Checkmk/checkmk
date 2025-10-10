#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.sap_hana_connect import (
    check_sap_hana_connect,
    discover_sap_hana_connect,
    parse_sap_hana_connect,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
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
            ],
            [("H00 00", {}), ("H11 11", {}), ("H22 22", {}), ("H33 33", {}), ("H44 44", {})],
        ),
    ],
)
def test_discover_sap_hana_connect(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for sap_hana_connect check."""
    parsed = parse_sap_hana_connect(string_table)
    result = list(discover_sap_hana_connect(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "H00 00",
            {},
            [
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
            ],
            [
                (
                    0,
                    "Standby: OK\nODBC Driver Version: not found, Server Node: not found, Timestamp: not found",
                )
            ],
        ),
        (
            "H11 11",
            {},
            [
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
            ],
            [
                (
                    0,
                    "Worker: OK\nODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                )
            ],
        ),
        (
            "H22 22",
            {},
            [
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
            ],
            [
                (
                    0,
                    "Standby: OK\nODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                )
            ],
        ),
        (
            "H33 33",
            {},
            [
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
            ],
            [
                (
                    2,
                    "No connect\nODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                )
            ],
        ),
        (
            "H44 44",
            {},
            [
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
            ],
            [
                (
                    3,
                    "Wrong Password Error connecting to ODBC Driver\nODBC Driver Version: not found, Server Node: not found, Timestamp: not found",
                )
            ],
        ),
    ],
)
def test_check_sap_hana_connect(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for sap_hana_connect check."""
    parsed = parse_sap_hana_connect(string_table)
    result = list(check_sap_hana_connect(item, params, parsed))
    assert result == expected_results
