#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("info, expected_parsed", [((
    [[
        "https_t3test.tgic.de", "FRONTEND", "", "", "0", "0", "2000", "invalid value", "0", "0",
        "0", "0", "0", "", "", "", "", "UP", "", "", "", "", "", "", "", "", "1", "2", "0", "", "",
        "", "0", "0", "0", "0", "", "", "", "0", "0", "0", "0", "0", "0", "", "0", "0", "0", "", "",
        "0", "0", "0", "0", "", "", "", "", "", "", "", ""
    ]],
    {},
))])
def test_parse_haproxy(info, expected_parsed):
    data = Check("haproxy").run_parse(info)
    assert data == expected_parsed


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "https_t3test.tgic.de",
        [[
            "# pxname", "svname", "qcur", "qmax", "scur", "smax", "slim", "stot", "bin", "bout",
            "dreq", "dresp", "ereq", "econ", "eresp", "wretr", "wredis", "status", "weight", "act",
            "bck", "chkfail", "chkdown", "lastchg", "downtime", "qlimit", "pid", "iid", "sid",
            "throttle", "lbtot", "tracked", "type", "rate", "rate_lim", "rate_max", "check_status",
            "check_code", "check_duration", "hrsp_1xx", "hrsp_2xx", "hrsp_3xx", "hrsp_4xx",
            "hrsp_5xx", "hrsp_other", "hanafail", "req_rate", "req_rate_max", "req_tot", "cli_abrt",
            "srv_abrt", "comp_in", "comp_out", "comp_byp", "comp_rsp", "lastsess", "last_chk",
            "last_agt", "qtime", "ctime", "rtime", "ttime", ""
        ],
         [
             "https_t3test.tgic.de", "FRONTEND", "", "", "0", "0", "2000", "0", "0", "0", "0", "0",
             "0", "", "", "", "", "OPEN", "", "", "", "", "", "", "", "", "1", "2", "0",
             "", "", "", "0", "0", "0", "0", "", "", "", "0", "0", "0", "0", "0", "0", "", "0", "0",
             "0", "", "", "0", "0", "0", "0", "", "", "", "", "", "", "", ""
         ]],
        [(0, "Status: OPEN"), (0, "Session Rate: 0.00", [("session_rate", 0.0, None, None)])],
    ),
    (
        "https_t3test.tgic.de",
        [[
            "https_t3test.tgic.de", "FRONTEND", "", "", "0", "0", "2000", "0", "0", "0", "0", "0",
            "0", "", "", "", "", "STOP", "", "", "", "", "", "", "", "", "1", "2", "0", "", "", "",
            "0", "0", "0", "0", "", "", "", "0", "0", "0", "0", "0", "0", "", "0", "0", "0", "", "",
            "0", "0", "0", "0", "", "", "", "", "", "", "", ""
        ]],
        [(2, "Status: STOP"), (0, "Session Rate: 0.00", [("session_rate", 0.0, None, None)])],
    )
])
def test_haproxy_frontend(item, info, expected_result):
    data = Check("haproxy").run_parse(info)
    result = Check("haproxy.frontend").run_check(item, {}, data)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "t3test/t3test",
        [[
            "t3test", "t3test", "0", "0", "0", "0", "", "0", "0", "0", "", "0", "", "0", "0", "0",
            "0", "UP", "1", "1", "0", "0", "0", "363417", "0", "", "1", "3", "1", "", "0", "", "2",
            "0", "", "0", "L4OK", "", "0", "0", "0", "0", "0", "0", "0", "0", "", "", "", "0", "0",
            "", "", "", "", "-1", "", "", "0", "0", "0", "0", ""
        ]],
        [(0, "Status: UP"), (0, "Active"), (0, "Layer Check: L4OK"), (0, "Up since 4.2 d")],
    ),
    (
        "t3test/t3test",
        [[
            "t3test", "t3test", "0", "0", "0", "0", "", "0", "0", "0", "", "0", "", "0", "0", "0",
            "0", "UP", "1", "0", "1", "0", "0", "363417", "0", "", "1", "3", "1", "", "0", "", "2",
            "0", "", "0", "L4OK", "", "0", "0", "0", "0", "0", "0", "0", "0", "", "", "", "0", "0",
            "", "", "", "", "-1", "", "", "0", "0", "0", "0", ""
        ]],
        [(0, "Status: UP"), (0, "Backup"), (0, "Layer Check: L4OK"), (0, "Up since 4.2 d")],
    ),
    (
        "t3test/t3test",
        [[
            "t3test", "t3test", "0", "0", "0", "0", "", "0", "0", "0", "", "0", "", "0", "0", "0",
            "0", "UP", "1", "0", "0", "0", "0", "363417", "0", "", "1", "3", "1", "", "0", "", "2",
            "0", "", "0", "L4OK", "", "0", "0", "0", "0", "0", "0", "0", "0", "", "", "", "0", "0",
            "", "", "", "", "-1", "", "", "0", "0", "0", "0", ""
        ]],
        [(0, "Status: UP"), (2, "Neither active nor backup"), (0, "Layer Check: L4OK"),
         (0, "Up since 4.2 d")],
    ),
    (
        "t3test/t3test",
        [[
            "t3test", "t3test", "0", "0", "0", "0", "", "0", "0", "0", "", "0", "", "0", "0", "0",
            "0", "UP", "1", "1", "0", "0", "0", "None", "0", "", "1", "3", "1", "", "0", "", "2",
            "0", "", "0", "L4OK", "", "0", "0", "0", "0", "0", "0", "0", "0", "", "", "", "0", "0",
            "", "", "", "", "-1", "", "", "0", "0", "0", "0", ""
        ]],
        [(0, "Status: UP"), (0, "Active"), (0, "Layer Check: L4OK")],
    ),
    (
        "t3test/t3test",
        [[
            "t3test", "t3test", "0", "0", "0", "0", "", "0", "0", "0", "", "0", "", "0", "0", "0",
            "0", "MAINT", "1", "1", "0", "0", "0", "363417", "0", "", "1", "3", "1", "", "0", "",
            "2", "0", "", "0", "L4OK", "", "0", "0", "0", "0", "0", "0", "0", "0", "", "", "", "0",
            "0", "", "", "", "", "-1", "", "", "0", "0", "0", "0", ""
        ]],
        [(2, "Status: MAINT"), (0, "Active"), (0, "Layer Check: L4OK"), (0, "Up since 4.2 d")],
    )
])
def test_haproxy_server(item, info, expected_result):
    data = Check("haproxy").run_parse(info)
    result = Check("haproxy.server").run_check(item, {}, data)
    assert list(result) == expected_result
