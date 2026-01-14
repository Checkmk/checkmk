#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.base.legacy_checks.db2_bp_hitratios import (
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
def parsed_fixture(string_table: list[list[str]]) -> dict[str, Any]:
    """Parsed DB2 buffer pool data"""
    return parse_db2_bp_hitratios(string_table)


def test_discover_db2_bp_hitratios(parsed: dict[str, Any]) -> None:
    """Test DB2 buffer pool discovery finds IBMDEFAULTBP buffer pool"""
    discovered = list(discover_db2_bp_hitratios(parsed))
    assert len(discovered) == 1
    assert discovered[0][0] == "serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP"
    assert discovered[0][1] == {}  # Empty parameters


def test_check_db2_bp_hitratios_normal_ratios(parsed: dict[str, Any]) -> None:
    """Test DB2 buffer pool check with normal hit ratios"""
    item = "serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP"
    result = list(check_db2_bp_hitratios(item, {}, parsed))

    assert len(result) == 4  # Total, Data, Index, XDA ratios

    # Check Total hit ratio
    total_result = result[0]
    assert total_result[0] == 0  # OK state
    assert total_result[1] == "Total: 83.62%"
    assert total_result[2] == [("total_hitratio", 83.62, None, None, 0, 100)]

    # Check Data hit ratio
    data_result = result[1]
    assert data_result[0] == 0  # OK state
    assert data_result[1] == "Data: 78.70%"
    assert data_result[2] == [("data_hitratio", 78.7, None, None, 0, 100)]

    # Check Index hit ratio
    index_result = result[2]
    assert index_result[0] == 0  # OK state
    assert index_result[1] == "Index: 99.74%"
    assert index_result[2] == [("index_hitratio", 99.74, None, None, 0, 100)]

    # Check XDA hit ratio
    xda_result = result[3]
    assert xda_result[0] == 0  # OK state
    assert xda_result[1] == "XDA: 50.00%"
    assert xda_result[2] == [("xda_hitratio", 50.0, None, None, 0, 100)]


def test_check_db2_bp_hitratios_missing_db(parsed: dict[str, Any]) -> None:
    """Test DB2 buffer pool check for non-existent database"""
    item = "nonexistent:IBMDEFAULTBP"

    # Should raise IgnoreResultsError for missing database
    with pytest.raises(Exception):  # IgnoreResultsError
        list(check_db2_bp_hitratios(item, {}, parsed))


def test_check_db2_bp_hitratios_missing_bufferpool(parsed: dict[str, Any]) -> None:
    """Test DB2 buffer pool check for non-existent buffer pool"""
    item = "serv0:ABC DPF 0 foo1.bar2.baz3 0:NONEXISTENT"
    result = list(check_db2_bp_hitratios(item, {}, parsed))
    assert len(result) == 0  # No results for missing buffer pool


def test_parse_db2_bp_hitratios_structure(string_table: list[list[str]]) -> None:
    """Test DB2 buffer pool parsing creates correct structure"""
    parsed = parse_db2_bp_hitratios(string_table)

    # Should have one database instance with DPF mode naming
    assert len(parsed) == 1
    assert "serv0:ABC DPF 0 foo1.bar2.baz3 0" in parsed

    # Check structure of parsed data
    db_data = parsed["serv0:ABC DPF 0 foo1.bar2.baz3 0"]
    assert len(db_data) == 2  # Header + one buffer pool

    # Check header
    headers = db_data[0]
    expected_headers = [
        "BP_NAME",
        "TOTAL_HIT_RATIO_PERCENT",
        "DATA_HIT_RATIO_PERCENT",
        "INDEX_HIT_RATIO_PERCENT",
        "XDA_HIT_RATIO_PERCENT",
    ]
    assert headers == expected_headers

    # Check buffer pool data
    bp_data = db_data[1]
    assert bp_data[0] == "IBMDEFAULTBP"
    assert bp_data[1] == "83.62"  # Total hit ratio
    assert bp_data[2] == "78.70"  # Data hit ratio
    assert bp_data[3] == "99.74"  # Index hit ratio
    assert bp_data[4] == "50.00"  # XDA hit ratio


def test_check_db2_bp_hitratios_dash_values() -> None:
    """Test DB2 buffer pool check handles dash values correctly"""
    # Create test data with dash values
    test_data = [
        ["[[[testdb:DB1]]]"],
        [
            "BP_NAME",
            "TOTAL_HIT_RATIO_PERCENT",
            "DATA_HIT_RATIO_PERCENT",
            "INDEX_HIT_RATIO_PERCENT",
            "XDA_HIT_RATIO_PERCENT",
        ],
        ["TESTBP", "95.50", "-", "100.00", "-"],  # Dash values should become 0
    ]

    parsed = parse_db2_bp_hitratios(test_data)
    item = "testdb:DB1:TESTBP"
    result = list(check_db2_bp_hitratios(item, {}, parsed))

    assert len(result) == 4

    # Check that dash values become 0.0
    data_result = result[1]  # Data hit ratio
    assert data_result[1] == "Data: 0%"
    assert data_result[2] == [("data_hitratio", 0.0, None, None, 0, 100)]

    xda_result = result[3]  # XDA hit ratio
    assert xda_result[1] == "XDA: 0%"
    assert xda_result[2] == [("xda_hitratio", 0.0, None, None, 0, 100)]


def test_check_db2_bp_hitratios_comma_decimal() -> None:
    """Test DB2 buffer pool check handles comma decimal separators"""
    # Create test data with comma decimal separators
    test_data = [
        ["[[[testdb:DB2]]]"],
        [
            "BP_NAME",
            "TOTAL_HIT_RATIO_PERCENT",
            "DATA_HIT_RATIO_PERCENT",
            "INDEX_HIT_RATIO_PERCENT",
            "XDA_HIT_RATIO_PERCENT",
        ],
        ["TESTBP", "95,75", "90,25", "99,99", "85,50"],  # Comma decimals
    ]

    parsed = parse_db2_bp_hitratios(test_data)
    item = "testdb:DB2:TESTBP"
    result = list(check_db2_bp_hitratios(item, {}, parsed))

    assert len(result) == 4

    # Check that comma decimals are converted properly
    total_result = result[0]
    assert total_result[1] == "Total: 95.75%"
    assert total_result[2] == [("total_hitratio", 95.75, None, None, 0, 100)]


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
        ["IBMSYSTEMBP4K", "98.00", "95.00", "99.50", "90.00"],  # Should be filtered
        ["CUSTOMBP", "92.00", "88.00", "98.00", "80.00"],
    ]

    parsed = parse_db2_bp_hitratios(test_data)
    discovered = list(discover_db2_bp_hitratios(parsed))

    # Should discover 2 buffer pools (excluding IBMSYSTEMBP4K)
    assert len(discovered) == 2
    discovered_names = [item[0] for item in discovered]
    assert any("IBMDEFAULTBP" in name for name in discovered_names)
    assert any("CUSTOMBP" in name for name in discovered_names)
    assert not any("IBMSYSTEMBP4K" in name for name in discovered_names)
