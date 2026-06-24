#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks import ups_bat_temp
from cmk.legacy_checks.ups_bat_temp import (
    check_ups_bat_temp,
    discover_ups_bat_temp,
    parse_ups_bat_temp,
)


@pytest.fixture(name="value_store_patch")
def _value_store_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ups_bat_temp, "get_value_store", dict)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["1", "25"], ["2", "27"]], [Service(item="Battery 1"), Service(item="Battery 2")]),
        # First sensor reports 0 -> no services discovered at all
        ([["1", "0"], ["2", "27"]], []),
        ([], []),
    ],
)
def test_discover_ups_bat_temp(string_table: StringTable, expected: list[Service]) -> None:
    assert list(discover_ups_bat_temp(parse_ups_bat_temp(string_table))) == expected


def test_check_ups_bat_temp_ok(value_store_patch: None) -> None:
    results = list(
        check_ups_bat_temp("Battery 1", {"levels": (40.0, 50.0)}, [["1", "25"], ["2", "27"]])
    )
    assert Metric("temp", 25.0, levels=(40.0, 50.0)) in results
    assert [r.state for r in results if isinstance(r, Result)] == [State.OK, State.OK]


def test_check_ups_bat_temp_crit(value_store_patch: None) -> None:
    results = list(check_ups_bat_temp("Battery 1", {"levels": (40.0, 50.0)}, [["1", "60"]]))
    assert Metric("temp", 60.0, levels=(40.0, 50.0)) in results
    assert State.CRIT in {r.state for r in results if isinstance(r, Result)}


def test_check_ups_bat_temp_item_not_found(value_store_patch: None) -> None:
    assert list(check_ups_bat_temp("Battery 9", {"levels": (40.0, 50.0)}, [["1", "25"]])) == []
