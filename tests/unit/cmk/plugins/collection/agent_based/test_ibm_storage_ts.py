#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import ibm_storage_ts as plugin

STRING_TABLE_OK = [
    [["TS3100", "IBM", "F.01"]],
    [["3"]],
    [["1", "3", "L2U7777777", "2", "0", "0", "No error"]],
    [["1", "99WT888888", "0", "0", "0", "0"]],
]

STRING_TABLE_NOK = [
    [["TS3100", "IBM", "F.01"]],
    [["5"]],
    [["1", "4", "L2U7777777", "2", "0", "0", "No error"]],
    [["1", "99WT888888", "1", "2", "3", "4"]],
]


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="IBM TS3100, Version F.01")],
            id="ok",
        ),
    ],
)
def test_ibm_storage_ts_info(
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    assert list(plugin.check_ibm_storage_ts(section=string_table)) == expected_result


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="Device Status: Ok")],
            id="ok",
        ),
        pytest.param(
            STRING_TABLE_NOK,
            [Result(state=State.CRIT, summary="Device Status: critical")],
            id="nok",
        ),
    ],
)
def test_ibm_storage_ts_status(
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    assert list(plugin.check_ibm_storage_ts_status(section=string_table)) == expected_result


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="Device L2U7777777, Status: Ok, Drives: 2")],
            id="ok",
        ),
        pytest.param(
            STRING_TABLE_NOK,
            [
                Result(
                    state=State.WARN, summary="Device L2U7777777, Status: non-critical, Drives: 2"
                )
            ],
            id="nok",
        ),
    ],
)
def test_ibm_storage_ts_library(
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    assert (
        list(plugin.check_ibm_storage_ts_library(section=string_table, item="1")) == expected_result
    )


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_OK,
            [Result(state=State.OK, summary="S/N: 99WT888888")],
            id="ok",
        ),
        pytest.param(
            STRING_TABLE_NOK,
            [
                Result(state=State.OK, summary="S/N: 99WT888888"),
                Result(state=State.CRIT, summary="2 hard write errors"),
                Result(state=State.WARN, summary="1 recovered write errors"),
                Result(state=State.CRIT, summary="4 hard read errors"),
                Result(state=State.WARN, summary="3 recovered read errors"),
            ],
            id="nok",
        ),
    ],
)
def test_ibm_storage_ts_drive(
    as_path: Callable[[str], Path],
    string_table: Sequence[StringTable],
    expected_result: CheckResult,
) -> None:
    assert (
        list(plugin.check_ibm_storage_ts_drive(section=string_table, item="1")) == expected_result
    )


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [["3100 Storage", "IBM", "v1.2.3"]],
                ["3"],
                [
                    ["0", "3", "1234567890", "2", "0", "2", ""],
                    ["1", "3", "1234567891", "2", "2", "2", "Message 2"],
                ],
                [["0", "9876543210", "0", "0", "0", "0"], ["1", "9876543211", "3", "4", "5", "6"]],
            ],
            [Service()],
        ),
    ],
)
def test_inventory_ibm_storage_ts(
    string_table: Sequence[list[list[str]]],
    expected_discoveries: Sequence[Service],
) -> None:
    """Test discovery function for ibm_storage_ts check."""
    parsed = plugin.parse_ibm_storage_ts(string_table)
    result = list(plugin.discover_ibm_storage_ts(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "string_table, expected_results",
    [
        (
            [
                [["3100 Storage", "IBM", "v1.2.3"]],
                ["3"],
                [
                    ["0", "3", "1234567890", "2", "0", "2", ""],
                    ["1", "3", "1234567891", "2", "2", "2", "Message 2"],
                ],
                [["0", "9876543210", "0", "0", "0", "0"], ["1", "9876543211", "3", "4", "5", "6"]],
            ],
            [Result(state=State.OK, summary="IBM 3100 Storage, Version v1.2.3")],
        ),
    ],
)
def test_check_ibm_storage_ts(
    string_table: Sequence[list[list[str]]],
    expected_results: CheckResult,
) -> None:
    """Test check function for ibm_storage_ts check."""
    parsed = plugin.parse_ibm_storage_ts(string_table)
    result = list(plugin.check_ibm_storage_ts(parsed))
    assert result == expected_results
