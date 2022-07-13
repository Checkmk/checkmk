#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.base.plugins.agent_based.kemp_loadmaster_realserver as klr
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

STRING_TABLE = [
    ["10.20.30.101", "1"],
    ["10.20.30.102", "1"],
    ["10.20.30.101", "1"],
    ["10.20.30.102", "1"],
    ["10.20.30.101", "1"],
    ["10.20.30.102", "1"],
]

SECTION: klr.Section = {
    "10.20.30.101": klr.RealServer(
        ip_address="10.20.30.101",
        state=State.OK,
        state_txt="in service",
    ),
    "10.20.30.102": klr.RealServer(
        ip_address="10.20.30.102",
        state=State.OK,
        state_txt="in service",
    ),
}


def test_parse() -> None:
    assert SECTION == klr.parse_kemp_loadmaster_realserver(STRING_TABLE)


def test_discovery() -> None:
    assert list(klr.discover_kemp_loadmaster_realserver(SECTION)) == [
        Service(item="10.20.30.101"),
        Service(item="10.20.30.102"),
    ]


def test_check() -> None:
    assert list(klr.check_kemp_loadmaster_realserver("10.20.30.101", SECTION)) == [
        Result(state=State.OK, summary="In Service"),
    ]
