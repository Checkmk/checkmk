#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.agent_based.v3_unstable import ParseFailure
from cmk.plugins.aruba.agent_based import aruba_fans

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
) -> None:
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
) -> None:
    section = aruba_fans.parse_aruba_fans(string_table)
    assert list(aruba_fans.check_aruba_fan_status(item, section)) == result


UNKNOWN_STATE_DATA = [
    ["1", "0", "1", "5", "0"],
    ["2", "0", "1", "7", "0"],
]


def test_a_fan_with_an_unknown_state_is_still_discovered() -> None:
    section = aruba_fans.parse_aruba_fans(UNKNOWN_STATE_DATA)

    discovered = list(aruba_fans.discover_aruba_fan_status(section))

    assert discovered == [Service(item="000001"), Service(item="000002")]


def test_a_fan_with_an_unknown_state_leaves_the_other_fans_intact() -> None:
    section = aruba_fans.parse_aruba_fans(UNKNOWN_STATE_DATA)

    results = list(aruba_fans.check_aruba_fan_status("000001", section))

    assert results == [
        Result(state=State.OK, summary="Fan Status: OK"),
        Result(state=State.OK, summary="Type: MM"),
        Result(state=State.OK, summary="Tray: 0"),
    ]


@pytest.mark.parametrize(
    "entry, expected",
    [
        pytest.param(
            ["2", "0", "1", "7", "0"],
            [
                "Could not parse 'hpicfFanState': '7' is not a valid FanState",
                "Type: MM",
                "Tray: 0",
            ],
            id="unknown state",
        ),
        pytest.param(
            ["2", "0", "9", "0", "0"],
            [
                "Fan Status: Failed",
                "Could not parse 'hpicfFanType': '9' is not a valid FanType",
                "Tray: 0",
            ],
            id="unknown type",
        ),
        pytest.param(
            ["2", "x", "1", "5", "0"],
            [
                "Fan Status: OK",
                "Type: MM",
                "Could not parse 'hpicfFanTray': invalid literal for int() with base 10: 'x'",
            ],
            id="tray not a number",
        ),
        pytest.param(
            ["2", "0", "1", "5", "x"],
            [
                "Fan Status: OK",
                "Type: MM",
                "Tray: 0",
                "Could not parse 'hpicfFanNumFailures': invalid literal for int() with base 10: 'x'",
            ],
            id="failures not a number",
        ),
    ],
)
def test_an_unparsable_value_is_shown_next_to_the_others(
    entry: list[str], expected: list[str]
) -> None:
    section = aruba_fans.parse_aruba_fans([entry])

    results = list(aruba_fans.check_aruba_fan_status("000002", section))

    assert [r.summary if isinstance(r, Result) else str(r) for r in results] == expected


def test_an_unknown_type_keeps_the_state_of_a_failed_fan() -> None:
    section = aruba_fans.parse_aruba_fans([["2", "0", "9", "0", "0"]])

    results = list(aruba_fans.check_aruba_fan_status("000002", section))

    assert results[0] == Result(state=State.CRIT, summary="Fan Status: Failed")
    assert isinstance(results[1], ParseFailure)


@pytest.mark.parametrize(
    "entry, expected",
    [
        pytest.param(
            ["2", "0", "1", "5", ""],
            [
                Result(state=State.OK, summary="Fan Status: OK"),
                Result(state=State.OK, summary="Type: MM"),
                Result(state=State.OK, summary="Tray: 0"),
            ],
            id="no failures count",
        ),
        pytest.param(
            ["2", "", "1", "5", "2"],
            [
                Result(state=State.OK, summary="Fan Status: OK"),
                Result(state=State.OK, summary="Type: MM"),
                Result(state=State.OK, summary="Failures: 2"),
            ],
            id="no tray",
        ),
    ],
)
def test_a_value_the_device_leaves_out_is_not_a_failure(
    entry: list[str], expected: list[Result]
) -> None:
    section = aruba_fans.parse_aruba_fans([entry])

    results = list(aruba_fans.check_aruba_fan_status("000002", section))

    assert results == expected
