#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.hp_proliant_mem import (
    check_hp_proliant_mem,
    discovery_hp_proliant_mem,
    Module,
)

SECTION = {
    "0": Module(
        number="0",
        board="0",
        cpu_num=1,
        size=4294967296,
        typ="DIMM DDR3",
        serial="",
        status="good",
        condition="ok",
    ),
    "3": Module(
        number="3",
        board="0",
        cpu_num=1,
        size=0,
        typ="DIMM DDR3",
        serial="",
        status="  notPresent",
        condition="other",
    ),
    "8": Module(
        number="8",
        board="0",
        cpu_num=2,
        size=4294967296,
        typ="DIMM DDR3",
        serial="",
        status="good",
        condition="ok",
    ),
    "9": Module(
        number="9",
        board="0",
        cpu_num=2,
        size=0,
        typ="DIMM DDR3",
        serial="",
        status="  notPresent",
        condition="other",
    ),
}


def test_discovery() -> None:
    assert list(discovery_hp_proliant_mem(SECTION)) == [
        Service(item="0"),
        Service(item="8"),
    ]


def test_check() -> None:
    assert list(check_hp_proliant_mem("0", SECTION)) == [
        Result(state=State.OK, summary="Board: 0"),
        Result(state=State.OK, summary="Number: 0"),
        Result(state=State.OK, summary="Type: DIMM DDR3"),
        Result(state=State.OK, summary="Size: 4.00 GiB"),
        Result(state=State.OK, summary="Status: good"),
        Result(state=State.OK, summary="Condition: ok"),
    ]
