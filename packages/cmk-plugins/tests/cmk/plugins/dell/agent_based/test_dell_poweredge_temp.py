#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.dell.agent_based import dell_poweredge_temp
from cmk.plugins.dell.agent_based.dell_poweredge_temp import (
    check_dell_poweredge_temp,
    discover_dell_poweredge_temp,
    parse_dell_poweredge_temp,
)

STRING_TABLE = [
    ["1", "1", "2", "3", "170", "System Board Inlet Temp", "470", "420", "30", "-70"],
    ["1", "2", "2", "3", "300", "System Board Exhaust Temp", "750", "700", "80", "30"],
    ["1", "3", "1", "2", "", "CPU1 Temp", "", "", "", ""],
    ["1", "4", "1", "2", "", "CPU2 Temp", "", "", "", ""],
]


@pytest.fixture(name="empty_value_store")
def empty_value_store_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, object] = {}
    monkeypatch.setattr(dell_poweredge_temp, "get_value_store", lambda: store)


def test_parse_dell_poweredge_temp() -> None:
    assert parse_dell_poweredge_temp(STRING_TABLE) == STRING_TABLE


@pytest.mark.parametrize(
    "string_table, expected_items",
    [
        (
            STRING_TABLE,
            {"System Board Exhaust", "System Board Inlet"},
        ),
    ],
)
def test_discover_dell_poweredge_temp(string_table: StringTable, expected_items: set[str]) -> None:
    parsed = parse_dell_poweredge_temp(string_table)
    result = list(discover_dell_poweredge_temp(parsed))
    assert all(isinstance(s, Service) for s in result)
    assert {s.item for s in result} == expected_items


def test_discover_filters_unknown_state() -> None:
    table = [
        ["1", "1", "1", "3", "170", "Unknown Sensor", "470", "420", "30", "-70"],
        ["1", "2", "2", "3", "300", "Good Sensor", "750", "700", "80", "30"],
    ]
    result = list(discover_dell_poweredge_temp(table))
    assert len(result) == 1
    assert result[0].item == "Good Sensor"


def test_discover_temp_suffix_trimming() -> None:
    table = [
        ["1", "1", "2", "3", "250", "Processor 1 Temp", "700", "600", "200", "100"],
        ["1", "2", "2", "3", "280", "Memory Module", "700", "600", "200", "100"],
    ]
    discovered = list(discover_dell_poweredge_temp(table))
    assert len(discovered) == 2
    items = {s.item for s in discovered}
    assert "Processor 1" in items
    assert "Memory Module" in items


def test_discover_fallback_naming_without_location() -> None:
    table = [["2", "5", "2", "3", "350", "", "700", "600", "200", "100"]]
    discovered = list(discover_dell_poweredge_temp(table))
    assert len(discovered) == 1
    assert discovered[0].item == "2-5"


@pytest.mark.parametrize(
    "item, expected_temp",
    [
        ("System Board Exhaust", 30.0),
        ("System Board Inlet", 17.0),
    ],
)
def test_check_dell_poweredge_temp_normal(
    item: str, expected_temp: float, empty_value_store: None
) -> None:
    parsed = parse_dell_poweredge_temp(STRING_TABLE)
    result = list(check_dell_poweredge_temp(item, {}, parsed))
    temp_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]
    assert any(r.state == State.OK for r in temp_results)
    assert any(m.name == "temp" and m.value == expected_temp for m in metrics)


def test_check_dell_poweredge_temp_missing_reading() -> None:
    table = [["1", "3", "2", "3", "", "CPU1 Temp", "", "", "", ""]]
    result = list(check_dell_poweredge_temp("CPU1", {}, table))
    assert len(result) == 0


def test_check_dell_poweredge_temp_nonexistent_item() -> None:
    parsed = parse_dell_poweredge_temp(STRING_TABLE)
    result = list(check_dell_poweredge_temp("Nonexistent Sensor", {}, parsed))
    assert len(result) == 0


def test_check_dell_poweredge_temp_warning_state(empty_value_store: None) -> None:
    table = [["1", "1", "2", "4", "800", "Hot Sensor", "700", "600", "200", "100"]]
    result = list(check_dell_poweredge_temp("Hot Sensor", {}, table))
    states = [r.state for r in result if isinstance(r, Result)]
    assert State.WARN in states


def test_check_dell_poweredge_temp_critical_state(empty_value_store: None) -> None:
    table = [["1", "1", "2", "5", "900", "Critical Sensor", "700", "600", "200", "100"]]
    result = list(check_dell_poweredge_temp("Critical Sensor", {}, table))
    states = [r.state for r in result if isinstance(r, Result)]
    assert State.CRIT in states


def test_check_dell_poweredge_temp_no_thresholds(empty_value_store: None) -> None:
    table = [["1", "1", "2", "3", "250", "No Threshold Sensor", "", "", "", ""]]
    result = list(check_dell_poweredge_temp("No Threshold Sensor", {}, table))
    results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]
    assert any(r.state == State.OK for r in results)
    assert any(m.name == "temp" and m.value == 25.0 for m in metrics)
