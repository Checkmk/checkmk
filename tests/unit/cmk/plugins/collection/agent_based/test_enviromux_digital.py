#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.enviromux_digital import (
    check_enviromux_digital,
    discover_enviromux_digital,
)
from cmk.plugins.lib.enviromux import parse_enviromux_digital

STRING_TABLE = [
    ["0", "Digital Input #1", "1", "1"],
    ["1", "Digital Input #2", "1", "1"],
    ["2", "Digital Input #3", "1", "1"],
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="Digital Input #1 0"),
                Service(item="Digital Input #2 1"),
                Service(item="Digital Input #3 2"),
            ],
            id="For every digital sensor, a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_enviromux_digital(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_enviromux_digital(parse_enviromux_digital(section)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Result(state=State.OK, summary="Sensor Value is normal: open")],
            id="If the sensor value is equal to the normal/expected value, the check result is OK.",
        ),
        pytest.param(
            [["0", "Digital Input #1", "0", "1"]],
            [
                Result(
                    state=State.CRIT,
                    summary="Sensor Value is not normal: closed . It should be: open",
                )
            ],
            id="If the sensor value is not equal to the normal/expected value, the check result is CRIT.",
        ),
    ],
)
def test_check_enviromux_digital(
    section: StringTable,
    expected_discovery_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_enviromux_digital(
                item="Digital Input #1 0",
                section=parse_enviromux_digital(section),
            )
        )
        == expected_discovery_result
    )
