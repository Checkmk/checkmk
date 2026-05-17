#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.db2.agent_based.db2_bp_hitratios import (
    check_db2_bp_hitratios,
    discover_db2_bp_hitratios,
    parse_db2_bp_hitratios,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for DB2 buffer pool hit ratios"""
    return [
        ["[[[serv0:ABC]]]"],
        ["node", "0", "foo1.bar2.baz3", "0"],
        [
            "BP_NAME",
            "TOTAL_HIT_RATIO_PERCENT",
            "DATA_HIT_RATIO_PERCENT",
            "INDEX_HIT_RATIO_PERCENT",
            "XDA_HIT_RATIO_PERCENT",
        ],
        ["IBMDEFAULTBP", "83.62", "78.70", "99.74", "50.00"],
        ["[[[serv1:XYZ]]]"],
        ["node", "0", "foo1.bar2.baz3", "0"],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> Mapping[str, list[list[str]]]:
    """Parsed DB2 buffer pool data"""
    return parse_db2_bp_hitratios(string_table)


def test_discover_db2_bp_hitratios(parsed: Mapping[str, list[list[str]]]) -> None:
    """Test DB2 buffer pool discovery finds IBMDEFAULTBP buffer pool"""
    discovered = list(discover_db2_bp_hitratios(parsed))
    assert discovered == [Service(item="serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP")]


def test_check_db2_bp_hitratios_normal_ratios(parsed: Mapping[str, list[list[str]]]) -> None:
    """Test DB2 buffer pool check with normal hit ratios"""
    item = "serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP"
    result = list(check_db2_bp_hitratios(item, parsed))

    assert result == [
        Result(state=State.OK, summary="Total: 83.62%"),
        Metric("total_hitratio", 83.62, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Data: 78.70%"),
        Metric("data_hitratio", 78.7, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Index: 99.74%"),
        Metric("index_hitratio", 99.74, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="XDA: 50.00%"),
        Metric("xda_hitratio", 50.0, boundaries=(0.0, 100.0)),
    ]


def test_check_db2_bp_hitratios_missing_db(parsed: Mapping[str, list[list[str]]]) -> None:
    """Test DB2 buffer pool check for non-existent database"""
    item = "nonexistent:IBMDEFAULTBP"

    with pytest.raises(IgnoreResultsError):
        list(check_db2_bp_hitratios(item, parsed))


def test_check_db2_bp_hitratios_missing_bufferpool(parsed: Mapping[str, list[list[str]]]) -> None:
    """Test DB2 buffer pool check for non-existent buffer pool"""
    item = "serv0:ABC DPF 0 foo1.bar2.baz3 0:NONEXISTENT"
    result = list(check_db2_bp_hitratios(item, parsed))
    assert result == []


def test_parse_db2_bp_hitratios_structure(string_table: list[list[str]]) -> None:
    """Test DB2 buffer pool parsing creates correct structure"""
    parsed = parse_db2_bp_hitratios(string_table)

    assert len(parsed) == 1
    assert "serv0:ABC DPF 0 foo1.bar2.baz3 0" in parsed

    db_data = parsed["serv0:ABC DPF 0 foo1.bar2.baz3 0"]
    assert len(db_data) == 2  # Header + one buffer pool

    headers = db_data[0]
    expected_headers = [
        "BP_NAME",
        "TOTAL_HIT_RATIO_PERCENT",
        "DATA_HIT_RATIO_PERCENT",
        "INDEX_HIT_RATIO_PERCENT",
        "XDA_HIT_RATIO_PERCENT",
    ]
    assert headers == expected_headers

    bp_data = db_data[1]
    assert bp_data[0] == "IBMDEFAULTBP"
    assert bp_data[1] == "83.62"
    assert bp_data[2] == "78.70"
    assert bp_data[3] == "99.74"
    assert bp_data[4] == "50.00"


def test_check_db2_bp_hitratios_dash_values() -> None:
    """Test DB2 buffer pool check handles dash values correctly"""
    test_data = [
        ["[[[testdb:DB1]]]"],
        [
            "BP_NAME",
            "TOTAL_HIT_RATIO_PERCENT",
            "DATA_HIT_RATIO_PERCENT",
            "INDEX_HIT_RATIO_PERCENT",
            "XDA_HIT_RATIO_PERCENT",
        ],
        ["TESTBP", "95.50", "-", "100.00", "-"],
    ]

    parsed = parse_db2_bp_hitratios(test_data)
    item = "testdb:DB1:TESTBP"
    result = list(check_db2_bp_hitratios(item, parsed))

    assert result == [
        Result(state=State.OK, summary="Total: 95.50%"),
        Metric("total_hitratio", 95.5, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Data: 0%"),
        Metric("data_hitratio", 0.0, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="Index: 100.00%"),
        Metric("index_hitratio", 100.0, boundaries=(0.0, 100.0)),
        Result(state=State.OK, summary="XDA: 0%"),
        Metric("xda_hitratio", 0.0, boundaries=(0.0, 100.0)),
    ]


def test_check_db2_bp_hitratios_comma_decimal() -> None:
    """Test DB2 buffer pool check handles comma decimal separators"""
    test_data = [
        ["[[[testdb:DB2]]]"],
        [
            "BP_NAME",
            "TOTAL_HIT_RATIO_PERCENT",
            "DATA_HIT_RATIO_PERCENT",
            "INDEX_HIT_RATIO_PERCENT",
            "XDA_HIT_RATIO_PERCENT",
        ],
        ["TESTBP", "95,75", "90,25", "99,99", "85,50"],
    ]

    parsed = parse_db2_bp_hitratios(test_data)
    item = "testdb:DB2:TESTBP"
    result = list(check_db2_bp_hitratios(item, parsed))

    assert result[0] == Result(state=State.OK, summary="Total: 95.75%")
    assert result[1] == Metric("total_hitratio", 95.75, boundaries=(0.0, 100.0))


def test_discover_db2_bp_hitratios_filters_system_bp() -> None:
    """Test that IBMSYSTEMBP buffer pools are filtered from discovery"""
    test_data = [
        ["[[[testdb:DB3]]]"],
        [
            "BP_NAME",
            "TOTAL_HIT_RATIO_PERCENT",
            "DATA_HIT_RATIO_PERCENT",
            "INDEX_HIT_RATIO_PERCENT",
            "XDA_HIT_RATIO_PERCENT",
        ],
        ["IBMDEFAULTBP", "95.50", "90.00", "100.00", "85.00"],
        ["IBMSYSTEMBP4K", "98.00", "95.00", "99.50", "90.00"],
        ["CUSTOMBP", "92.00", "88.00", "98.00", "80.00"],
    ]

    parsed = parse_db2_bp_hitratios(test_data)
    discovered = list(discover_db2_bp_hitratios(parsed))

    assert len(discovered) == 2
    discovered_items = [service.item for service in discovered]
    assert any(item is not None and "IBMDEFAULTBP" in item for item in discovered_items)
    assert any(item is not None and "CUSTOMBP" in item for item in discovered_items)
    assert not any(item is not None and "IBMSYSTEMBP4K" in item for item in discovered_items)
