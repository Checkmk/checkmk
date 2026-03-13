#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.cisco_fantray import (
    check_cisco_fantray,
    parse_cisco_fantray,
)


@pytest.mark.parametrize(
    ("item", "section", "expected"),
    [
        (
            "FanModule-1",
            {"FanModule-1": (State.OK, "powered on")},
            [Result(state=State.OK, summary="Status: powered on")],
        ),
        (
            "FanModule-1",
            {"FanModule-1": (State.CRIT, "powered down")},
            [Result(state=State.CRIT, summary="Status: powered down")],
        ),
        (
            "FanModule-2",
            {"FanModule-1": (State.OK, "powered on")},
            [],
        ),
    ],
)
def test_check_cisco_fantray(
    item: str,
    section: list[list[str]],
    expected: list[Result],
) -> None:
    results = list(check_cisco_fantray(item, section))
    assert results == expected


@pytest.mark.parametrize(
    ("string_table", "expected"),
    [
        (
            [
                [["534", "2"]],
                [["534", "FanModule-1"]],
            ],
            {
                "FanModule-1": (State.OK, "powered on"),
            },
        ),
        (
            [
                [["534", "2"], ["113000534", "2"]],
                [["534", "FanModule-1"]],
            ],
            {
                "FanModule-1": (State.OK, "powered on"),
            },
        ),
        (
            [
                [["534", "2"]],
                [["534", ""]],
            ],
            {
                "534": (State.OK, "powered on"),
            },
        ),
        (
            [
                [["534", "2"]],
                [["534", "   "]],
            ],
            {
                "534": (State.OK, "powered on"),
            },
        ),
    ],
    ids=[
        "use name when status and name exist",
        "ignore status without matching name",
        "fallback to oid when name empty",
        "fallback to oid when name whitespace",
    ],
)
def test_parse_cisco_fantray(
    string_table: list[list[str]],
    expected: dict[str, tuple[State, str]],
) -> None:
    section = parse_cisco_fantray(string_table)
    assert section == expected


def test_parse_disambiguates_duplicate_names() -> None:
    string_table = [
        [["534", "2"], ["535", "3"]],
        [["534", "FanModule-1"], ["535", "FanModule-1"]],
    ]

    section = parse_cisco_fantray(string_table)

    assert section == {
        "FanModule-1-1": (State.OK, "powered on"),
        "FanModule-1-2": (State.CRIT, "powered down"),
    }
