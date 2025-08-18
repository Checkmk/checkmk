#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.cisco_sma.agent_based.resource_conservation import (
    _check_resource_conservation,
    _discover_resource_conservation,
    _parse_resource_conservation,
    ResourceConservation,
)


def test_discover_resource_conservation() -> None:
    assert list(_discover_resource_conservation(None)) == [Service()]
    assert list(_discover_resource_conservation(ResourceConservation.OFF)) == [Service()]
    assert list(_discover_resource_conservation(ResourceConservation.UNKNOWN)) == [Service()]


@pytest.mark.parametrize(
    "string_table, expected",
    (
        (
            [["1"]],
            [
                Result(state=State.OK, summary="Resource conservation mode off"),
            ],
        ),
        (
            [["2"]],
            [
                Result(state=State.WARN, summary="Resource conservation mode on (memory shortage)"),
            ],
        ),
        (
            [["3"]],
            [
                Result(
                    state=State.WARN, summary="Resource conservation mode on (queue space shortage)"
                ),
            ],
        ),
        (
            [["4"]],
            [
                Result(state=State.CRIT, summary="Resource conservation mode on (queue full)"),
            ],
        ),
        (
            [["29"]],
            [
                Result(state=State.UNKNOWN, summary="Resource conservation status unknown"),
            ],
        ),
    ),
)
def test_check_resource_conservation(
    string_table: StringTable,
    expected: CheckResult,
) -> None:
    rc = _parse_resource_conservation(string_table)
    assert list(_check_resource_conservation(rc)) == list(expected)
