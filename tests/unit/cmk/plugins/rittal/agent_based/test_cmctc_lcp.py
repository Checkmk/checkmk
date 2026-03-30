#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, StringTable
from cmk.plugins.rittal.agent_based import cmctc_lcp
from cmk.plugins.rittal.agent_based.cmctc_lcp import (
    check_cmctc_lcp_temp,
    discover_cmctc_lcp_access,
    discover_cmctc_lcp_current,
    discover_cmctc_lcp_position,
    discover_cmctc_lcp_status,
    discovery_cmctc_lcp_temp,
    parse_cmctc_lcp,
)

STRING_TABLE: list[StringTable] = [
    [
        ["1", "30", "4", "0", "130", "10", "70", "Power (PSM)"],
        ["2", "31", "4", "1", "0", "0", "0", "State (PSM)"],
        ["3", "32", "4", "2", "0", "0", "0", "Position (PSM)"],
        ["4", "30", "4", "0", "130", "10", "70", "Power (PSM)"],
        ["5", "31", "4", "1", "0", "0", "0", "State (PSM)"],
        ["6", "32", "4", "1", "0", "0", "0", "Position (PSM)"],
        ["7", "30", "4", "3", "130", "10", "70", "Power (PSM)"],
        ["8", "31", "4", "1", "0", "0", "0", "State (PSM)"],
        ["9", "32", "4", "1", "0", "0", "0", "Position (PSM)"],
    ],
    [
        ["1", "10", "4", "21", "65", "10", "35", "Temperatursensor"],
        ["2", "1", "1", "0", "0", "0", "0", "nicht verfuegbar"],
        ["", "", "", "", "", "", "", "Luefter"],
    ],
    [
        ["1", "4", "4", "1", "0", "0", "0", "Access sensor"],
        ["2", "1", "1", "0", "0", "0", "0", "nicht verfuegbar"],
        ["3", "1", "1", "0", "0", "0", "0", "nicht verfuegbar"],
        ["4", "10", "4", "24", "65", "10", "55", "Temperatursensor"],
    ],
    [],
]

SECTION = parse_cmctc_lcp(STRING_TABLE)


def test_discover_cmctc_lcp_access() -> None:
    expected_discovery: list[Service] = [
        Service(item="5.1"),
    ]
    assert list(discover_cmctc_lcp_access(SECTION)) == expected_discovery


def test_discover_cmctc_lcp_status() -> None:
    expected_discovery: list[Service] = [
        Service(item="3.2"),
        Service(item="3.5"),
        Service(item="3.8"),
    ]
    assert list(discover_cmctc_lcp_status(SECTION)) == expected_discovery


def test_discover_cmctc_lcp_position() -> None:
    expected_discovery: list[Service] = [
        Service(item="3.3"),
        Service(item="3.6"),
        Service(item="3.9"),
    ]
    assert list(discover_cmctc_lcp_position(SECTION)) == expected_discovery


def test_discover_cmctc_lcp_current() -> None:
    expected_discovery: list[Service] = [
        Service(item="3.1"),
        Service(item="3.4"),
        Service(item="3.7"),
    ]
    assert list(discover_cmctc_lcp_current(SECTION)) == expected_discovery


# Temperature sensor data: typeid "48" = "Server in 1", type "temp"
TEMP_STRING_TABLE: list[StringTable] = [
    [
        ["1", "48", "4", "21", "65", "10", "35", "Server in 1"],
    ],
    [],
    [],
    [],
]

TEMP_SECTION = parse_cmctc_lcp(TEMP_STRING_TABLE)


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, object] = {}
    monkeypatch.setattr(cmctc_lcp, "get_value_store", lambda: store)


def test_discover_cmctc_lcp_temp() -> None:
    # typeid "48" maps to type "temp", item name "Server in 1 - 3.1"
    services = list(discovery_cmctc_lcp_temp(TEMP_SECTION))
    assert services == [Service(item="Server in 1 - 3.1")]


def test_check_cmctc_lcp_temp_produces_results(empty_value_store: None) -> None:
    # Regression test for Werk 16246 / SUP-18502:
    # check_cmctc_lcp_temp was missing value_store and unique_name arguments when calling
    # check_temperature, causing a ValueError at runtime.
    # After the fix, the check must complete without raising an exception.
    results = list(check_cmctc_lcp_temp("Server in 1 - 3.1", {}, TEMP_SECTION))
    assert any(isinstance(r, (Result, Metric)) for r in results)


def test_check_cmctc_lcp_temp_temperature_value(empty_value_store: None) -> None:
    results = list(check_cmctc_lcp_temp("Server in 1 - 3.1", {}, TEMP_SECTION))
    metrics = [r for r in results if isinstance(r, Metric) and r.name == "temp"]
    assert metrics, "Expected a 'temp' metric"
    assert metrics[0].value == 21.0


def test_check_cmctc_lcp_temp_missing_item_returns_empty(empty_value_store: None) -> None:
    results = list(check_cmctc_lcp_temp("nonexistent", {}, TEMP_SECTION))
    assert results == []
