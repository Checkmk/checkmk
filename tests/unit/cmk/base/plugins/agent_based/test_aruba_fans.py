#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import aruba_fans
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

DATA = [
    ["1", "0", "0", "0", "3"],
    ["2", "0", "1", "1", "1"],
    ["3", "0", "2", "2", "1"],
    ["4", "1", "3", "3", "0"],
    ["5", "2", "4", "4", "0"],
    ["111001", "0", "5", "5", "0"],
    ["111002", "0", "6", "6", "1"],
    ["111003", "0", "0", "5", "0"],
    ["111004", "1", "4", "5", "0"],
    ["111005", "2", "4", "5", "0"],
]


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            DATA,
            [
                Service(item="000001"),
                Service(item="000002"),
                Service(item="000003"),
                Service(item="000004"),
                Service(item="000005"),
                Service(item="111001"),
                Service(item="111002"),
                Service(item="111003"),
                Service(item="111004"),
                Service(item="111005"),
            ],
        ),
    ],
)
def test_discover_aruba_fan_status(
    string_table: StringTable,
    result: DiscoveryResult,
):
    section = aruba_fans.parse_aruba_fans(string_table)
    assert list(aruba_fans.discover_aruba_fan_status(section)) == result


@pytest.mark.parametrize(
    "string_table, item, result",
    [
        (
            DATA,
            "000001",
            [
                Result(state=State.CRIT, summary="Fan Status: Failed"),
                Result(state=State.OK, summary="Type: Unknown"),
                Result(state=State.OK, summary="Tray: 0"),
                Result(state=State.OK, summary="Failures: 3"),
            ],
        ),
        (
            DATA,
            "000002",
            [
                Result(state=State.WARN, summary="Fan Status: Removed"),
                Result(state=State.OK, summary="Type: MM"),
                Result(state=State.OK, summary="Tray: 0"),
                Result(state=State.OK, summary="Failures: 1"),
            ],
        ),
        (
            DATA,
            "000003",
            [
                Result(state=State.WARN, summary="Fan Status: Off"),
                Result(state=State.OK, summary="Type: FM"),
                Result(state=State.OK, summary="Tray: 0"),
                Result(state=State.OK, summary="Failures: 1"),
            ],
        ),
        (
            DATA,
            "000004",
            [
                Result(state=State.WARN, summary="Fan Status: Underspeed"),
                Result(state=State.OK, summary="Type: IM"),
                Result(state=State.OK, summary="Tray: 1"),
            ],
        ),
        (
            DATA,
            "000005",
            [
                Result(state=State.WARN, summary="Fan Status: Overspeed"),
                Result(state=State.OK, summary="Type: PS"),
                Result(state=State.OK, summary="Tray: 2"),
            ],
        ),
        (
            DATA,
            "111001",
            [
                Result(state=State.OK, summary="Fan Status: OK"),
                Result(state=State.OK, summary="Type: Rollup"),
                Result(state=State.OK, summary="Tray: 0"),
            ],
        ),
        (
            DATA,
            "111002",
            [
                Result(state=State.OK, summary="Fan Status: MaxState"),
                Result(state=State.OK, summary="Type: Maxtype"),
                Result(state=State.OK, summary="Tray: 0"),
                Result(state=State.OK, summary="Failures: 1"),
            ],
        ),
        (
            DATA,
            "111003",
            [
                Result(state=State.OK, summary="Fan Status: OK"),
                Result(state=State.OK, summary="Type: Unknown"),
                Result(state=State.OK, summary="Tray: 0"),
            ],
        ),
        (
            DATA,
            "111004",
            [
                Result(state=State.OK, summary="Fan Status: OK"),
                Result(state=State.OK, summary="Type: PS"),
                Result(state=State.OK, summary="Tray: 1"),
            ],
        ),
        (
            DATA,
            "111005",
            [
                Result(state=State.OK, summary="Fan Status: OK"),
                Result(state=State.OK, summary="Type: PS"),
                Result(state=State.OK, summary="Tray: 2"),
            ],
        ),
    ],
)
def test_check_aruba_fan_status(
    string_table: StringTable,
    item: str,
    result: CheckResult,
):
    section = aruba_fans.parse_aruba_fans(string_table)
    assert list(aruba_fans.check_aruba_fan_status(item, section)) == result
