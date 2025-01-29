#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.cisco_fan import (
    check_cisco_fan,
    inventory_cisco_fan,
    parse_cisco_fan,
)


def _section() -> StringTable:
    return parse_cisco_fan(
        [
            ["Fan_1_rpm", "", "0"],
            ["Fan_2_rpm", "1", "1"],
            ["Fan_3_rpm", "999", "2"],
        ]
    )


def test_discovery_cisco_fan() -> None:
    assert list(inventory_cisco_fan(_section())) == [Service(item="Fan_2_rpm 1")]


def test_check_cisco_fan() -> None:
    assert list(check_cisco_fan("Fan_2_rpm 1", _section())) == [
        Result(state=State.OK, summary="Status: normal")
    ]
