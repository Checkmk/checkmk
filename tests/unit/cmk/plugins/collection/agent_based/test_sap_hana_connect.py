#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.utils.sectionname import SectionName

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
def test_sap_hana_connect_missing_serverdb(
    agent_based_plugins: AgentBasedPlugins, info: StringTable
) -> None:
    parse_function = agent_based_plugins.agent_sections[
        SectionName("sap_hana_connect")
    ].parse_function
    assert parse_function(info) == {
        "YYY 11": {
            "cmk_state": 0,
            "driver_version": "02.12.0025 (2022-05-06).",
            "message": "Worker: OK",
            "server_node": "lllllllllllll:30003",
            "timestamp": "2022-11-28 10:03:08",
        },
    }
