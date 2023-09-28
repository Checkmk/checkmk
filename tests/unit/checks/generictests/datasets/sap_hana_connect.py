#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "sap_hana_connect"

info = [
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

discovery = {"": [("H00 00", {}), ("H11 11", {}), ("H22 22", {}), ("H33 33", {}), ("H44 44", {})]}

checks = {
    "": [
        (
            "H00 00",
            {},
            [
                (
                    0,
                    "Standby: OK\nODBC Driver Version: not found, Server Node: not found, Timestamp: not found",
                    [],
                )
            ],
        ),
        (
            "H11 11",
            {},
            [
                (
                    0,
                    "Worker: OK\nODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                    [],
                )
            ],
        ),
        (
            "H22 22",
            {},
            [
                (
                    0,
                    "Standby: OK\nODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                    [],
                )
            ],
        ),
        (
            "H33 33",
            {},
            [
                (
                    2,
                    "No connect\nODBC Driver Version: SAP HDB 1.00 (2013-10-15)., Server Node: Hana-host:3inst13, Timestamp: 2013-11-12 15:44:55",
                    [],
                )
            ],
        ),
        (
            "H44 44",
            {},
            [
                (
                    3,
                    "Wrong Password Error connecting to ODBC Driver\nODBC Driver Version: not found, Server Node: not found, Timestamp: not found",
                    [],
                )
            ],
        ),
    ]
}
