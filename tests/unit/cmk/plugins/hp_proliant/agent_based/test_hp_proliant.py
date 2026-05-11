#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hp_proliant.agent_based.hp_proliant import (
    check_proliant_general,
    discover_proliant_general,
)


def test_hp_proliant_discovery() -> None:
    string_table = [["2", "2.60 May 23 2018", "CXX43801XX"]]
    assert list(discover_proliant_general(string_table)) == [Service()]


def test_hp_proliant_check() -> None:
    string_table = [["2", "2.60 May 23 2018", "CXX43801XX"]]
    assert list(check_proliant_general(string_table)) == [
        Result(
            state=State.OK,
            summary="Status: OK, Firmware: 2.60 May 23 2018, S/N: CXX43801XX",
        ),
    ]
