#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.ra32e_switch import (
    check_ra32e_switch,
    discover_ra32e_switch,
    parse_ra32e_switch,
)


@pytest.mark.parametrize(
    "info,result",
    [
        (
            [
                [
                    "1",
                    "1",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                ]
            ],
            [
                Service(item="Sensor 01"),
                Service(item="Sensor 02"),
                Service(item="Sensor 03"),
                Service(item="Sensor 04"),
                Service(item="Sensor 05"),
                Service(item="Sensor 06"),
                Service(item="Sensor 07"),
                Service(item="Sensor 08"),
                Service(item="Sensor 09"),
                Service(item="Sensor 10"),
                Service(item="Sensor 11"),
                Service(item="Sensor 12"),
                Service(item="Sensor 13"),
                Service(item="Sensor 14"),
                Service(item="Sensor 15"),
                Service(item="Sensor 16"),
            ],
        )
    ],
)
def test_ra32e_switch_discovery(info: StringTable, result: Sequence[Service]) -> None:
    section = parse_ra32e_switch(info)
    assert section is not None
    assert list(discover_ra32e_switch(section)) == result


def test_ra32e_switch_check_closed_no_rule() -> None:
    assert list(check_ra32e_switch("Sensor 01", {"state": "ignore"}, [["1"]])) == [
        Result(state=State.OK, summary="closed")
    ]


def test_ra32e_switch_check_open_expected_close() -> None:
    assert list(
        check_ra32e_switch(
            "Sensor 03",
            {"state": "closed"},
            [["1", "1", "0", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1"]],
        )
    ) == [Result(state=State.CRIT, summary="open (expected closed)")]


def test_ra32e_switch_check_no_input() -> None:
    assert list(check_ra32e_switch("Sensor 01", {"state": "ignore"}, [[""]])) == [
        Result(state=State.UNKNOWN, summary="unknown status")
    ]
