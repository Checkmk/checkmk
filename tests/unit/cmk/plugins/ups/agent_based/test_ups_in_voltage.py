#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_in_voltage import (
    discover_ups_in_voltage,
    parse_ups_in_voltage,
)
from cmk.plugins.ups.lib import check_ups_in_voltage


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["1", "230"], ["2", "0"]], [Service(item="1")]),
        ([], []),
    ],
)
def test_discover_ups_in_voltage(string_table: StringTable, expected: list[Service]) -> None:
    assert list(discover_ups_in_voltage(parse_ups_in_voltage(string_table))) == expected


def test_check_ups_in_voltage_ok() -> None:
    assert list(check_ups_in_voltage("1", {"levels_lower": (210.0, 180.0)}, [["1", "230"]])) == [
        Result(state=State.OK, summary="In voltage: 230V"),
        Metric("in_voltage", 230.0, boundaries=(150.0, None)),
    ]


def test_check_ups_in_voltage_warn() -> None:
    results = list(check_ups_in_voltage("1", {"levels_lower": (240, 200)}, [["1", "230"]]))
    assert results[0] == Result(
        state=State.WARN, summary="In voltage: 230V (warn/crit below 240V/200V)"
    )
    assert Metric("in_voltage", 230.0, boundaries=(150.0, None)) in results


def test_check_ups_in_voltage_crit() -> None:
    results = list(check_ups_in_voltage("1", {"levels_lower": (250, 240)}, [["1", "230"]]))
    assert results[0] == Result(
        state=State.CRIT, summary="In voltage: 230V (warn/crit below 250V/240V)"
    )


def test_check_ups_in_voltage_missing_item() -> None:
    assert list(check_ups_in_voltage("9", {"levels_lower": (210.0, 180.0)}, [["1", "230"]])) == []
