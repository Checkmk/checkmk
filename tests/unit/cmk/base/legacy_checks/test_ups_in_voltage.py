#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.ups_in_voltage import check_ups_in_voltage
from cmk.base.legacy_checks.ups_in_voltage import discover_ups_in_voltage
from cmk.plugins.ups.lib import parse_ups_voltage


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["1", "230"], ["2", "0"]], [("1", {})]),
        ([["1", "230"], ["2", ""], ["3", "0"]], [("1", {})]),
        ([["1", "230"], ["2", "NULL"]], [("1", {})]),
        ([["1", ""]], []),
        ([], []),
    ],
)
def test_discover_ups_in_voltage(
    string_table: StringTable, expected: list[tuple[str, dict[str, object]]]
) -> None:
    assert list(discover_ups_in_voltage(parse_ups_voltage(string_table))) == expected


def test_check_ups_in_voltage_ok() -> None:
    assert list(check_ups_in_voltage("1", {"levels_lower": (210.0, 180.0)}, [["1", "230"]])) == [
        (0, "In voltage: 230V", [("in_voltage", 230, None, None, 150, None)]),
    ]


def test_check_ups_in_voltage_warn() -> None:
    assert list(check_ups_in_voltage("1", {"levels_lower": (240, 200)}, [["1", "230"]])) == [
        (
            1,
            "In voltage: 230V (warn/crit below 240V/200V)",
            [("in_voltage", 230, None, None, 150, None)],
        ),
    ]


def test_check_ups_in_voltage_crit() -> None:
    assert list(check_ups_in_voltage("1", {"levels_lower": (250, 240)}, [["1", "230"]])) == [
        (
            2,
            "In voltage: 230V (warn/crit below 250V/240V)",
            [("in_voltage", 230, None, None, 150, None)],
        ),
    ]


def test_check_ups_in_voltage_missing_item() -> None:
    assert list(check_ups_in_voltage("9", {"levels_lower": (210.0, 180.0)}, [["1", "230"]])) == []


def test_check_ups_in_voltage_empty_value() -> None:
    assert (
        list(
            check_ups_in_voltage(
                "2",
                {"levels_lower": (210.0, 180.0)},
                parse_ups_voltage([["1", "230"], ["2", ""]]),
            )
        )
        == []
    )


def test_check_ups_in_voltage_zero_is_crit() -> None:
    assert list(
        check_ups_in_voltage("1", {"levels_lower": (240, 200)}, parse_ups_voltage([["1", "0"]]))
    ) == [
        (
            2,
            "In voltage: 0V (warn/crit below 240V/200V)",
            [("in_voltage", 0, None, None, 150, None)],
        ),
    ]
