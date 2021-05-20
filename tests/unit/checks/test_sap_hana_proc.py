#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
        ["39006", "webdispatcher", "4644", "", "YES", "0", "NONE"],
        ["39010", "compileserver", "3546", "", "YES", "0", "NONE"],
    ], {
        "HXE 90 SYSTEMDB - compileserver": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "3546",
            "port": "39010",
            "sql_port": 0
        },
        "HXE 90 SYSTEMDB - daemon": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "2384",
            "port": "39000",
            "sql_port": 0
        },
        "HXE 90 SYSTEMDB - webdispatcher": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "4644",
            "port": "39006",
            "sql_port": 0
        },
    }),
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["39000"],
    ], {}),
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["39000", "daemon", "2384", "", "YES", "a", "NONE"],
    ], {
        "HXE 90 SYSTEMDB - daemon": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "2384",
            "port": "39000",
            "sql_port": None
        },
    }),
])
def test_parse_sap_hana_proc(info, expected_result):
    result = Check("sap_hana_proc").run_parse(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
            ["39006", "webdispatcher", "4644", "", "YES", "0", "NONE"],
            ["39010", "compileserver", "3546", "", "YES", "0", "NONE"],
        ],
        [("HXE 90 SYSTEMDB - daemon", {
            "coordin": "NONE"
        }), ("HXE 90 SYSTEMDB - webdispatcher", {
            "coordin": "NONE"
        }), ("HXE 90 SYSTEMDB - compileserver", {
            "coordin": "NONE"
        })],
    ),
])
def test_inventory_sap_hana_proc(info, expected_result):
    section = Check("sap_hana_proc").run_parse(info)
    result = Check("sap_hana_proc").run_discovery(section)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, params, info, expected_result", [
    (
        "HXE 90 SYSTEMDB - daemon",
        {
            "coordin": "NONE"
        },
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
            ["39006", "webdispatcher", "4644", "", "YES", "0", "NONE"],
            ["39010", "compileserver", "3546", "", "YES", "0", "NONE"],
        ],
        [(0, "Port: 39000, PID: 2384")],
    ),
    (
        "HXE 90 SYSTEMDB - daemon",
        {
            "coordin": "NOT NONE"
        },
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
        ],
        [(0, "Port: 39000, PID: 2384"), (1, "Role: changed from NOT NONE to NONE")],
    ),
    (
        "HXE 90 SYSTEMDB - daemon",
        {
            "coordin": "NONE"
        },
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["39000", "daemon", "2384", "", "YES", "12", "NONE"],
        ],
        [(0, "Port: 39000, PID: 2384"), (0, "SQL-Port: 12")],
    ),
    (
        "HXE 90 SYSTEMDB - daemon",
        {
            "coordin": "SOMETHING"
        },
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["39000", "daemon", "2384", "", "NO", "0", "SOMETHING"],
        ],
        [(0, "Port: 39000, PID: 2384"), (0, "Role: SOMETHING"), (2, "not acting")],
    ),
])
def test_check_sap_hana_proc(item, params, info, expected_result):
    section = Check("sap_hana_proc").run_parse(info)
    result = Check("sap_hana_proc").run_check(item, params, section)
    assert list(result) == expected_result