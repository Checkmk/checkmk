#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc,import-untyped"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.stulz.agent_based.stulz_powerstate import (
    check_stulz_powerstate,
    discover_stulz_powerstate,
    parse_stulz_powerstate,
)

_STRING_TABLE: list[list[str]] = [
    ["1013.1.1.1", "1"],
    ["1013.1.2.1", "0"],
]


def test_discover_stulz_powerstate() -> None:
    parsed = parse_stulz_powerstate(_STRING_TABLE)
    assert list(discover_stulz_powerstate(parsed)) == [
        Service(item="1013.1.1.1"),
        Service(item="1013.1.2.1"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "1013.1.1.1",
            [
                Result(state=State.OK, summary="Device powered on"),
                Metric("state", 6),
            ],
        ),
        (
            "1013.1.2.1",
            [
                Result(state=State.OK, summary="Device powered off"),
                Metric("state", 2),
            ],
        ),
        ("does-not-exist", []),
    ],
)
def test_check_stulz_powerstate(item: str, expected_results: Sequence[Result | Metric]) -> None:
    parsed = parse_stulz_powerstate(_STRING_TABLE)
    assert list(check_stulz_powerstate(item, parsed)) == expected_results
