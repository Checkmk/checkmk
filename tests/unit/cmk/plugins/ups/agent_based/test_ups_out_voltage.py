#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_out_voltage import discover_ups_out_voltage
from cmk.plugins.ups.lib import check_ups_out_voltage, parse_ups_voltage


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["1", "230"], ["2", "0"]], [Service(item="1")]),
        ([["1", "230"], ["2", ""], ["3", "0"]], [Service(item="1")]),
        ([["1", "230"], ["2", "NULL"]], [Service(item="1")]),
        ([["1", ""]], []),
        ([], []),
    ],
)
def test_discover_ups_out_voltage(string_table: StringTable, expected: list[Service]) -> None:
    assert list(discover_ups_out_voltage(parse_ups_voltage(string_table))) == expected


def test_check_ups_out_voltage_ok() -> None:
    assert list(check_ups_out_voltage("1", {"levels_lower": (210.0, 180.0)}, [["1", "230"]])) == [
        Result(state=State.OK, summary="Out voltage: 230V"),
        Metric("out_voltage", 230.0),
    ]


def test_check_ups_out_voltage_warn() -> None:
    results = list(check_ups_out_voltage("1", {"levels_lower": (240, 200)}, [["1", "230"]]))
    assert results[0] == Result(
        state=State.WARN, summary="Out voltage: 230V (warn/crit below 240V/200V)"
    )
    assert Metric("out_voltage", 230.0) in results


def test_check_ups_out_voltage_missing_item() -> None:
    assert list(check_ups_out_voltage("9", {"levels_lower": (210.0, 180.0)}, [["1", "230"]])) == []


def test_check_ups_out_voltage_empty_value() -> None:
    assert (
        list(
            check_ups_out_voltage(
                "2",
                {"levels_lower": (210.0, 180.0)},
                parse_ups_voltage([["1", "230"], ["2", ""]]),
            )
        )
        == []
    )


def test_check_ups_out_voltage_zero_is_crit() -> None:
    results = list(
        check_ups_out_voltage("1", {"levels_lower": (240, 200)}, parse_ups_voltage([["1", "0"]]))
    )
    assert results[0] == Result(
        state=State.CRIT, summary="Out voltage: 0V (warn/crit below 240V/200V)"
    )
    assert Metric("out_voltage", 0.0) in results
