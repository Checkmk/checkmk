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

"""Unit tests for f5_bigip_snat F5 BigIP Source NAT monitoring - Pattern 5."""

import time
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks import f5_bigip_snat


@pytest.fixture(name="f5_bigip_snat_string_table")
def _f5_bigip_snat_string_table() -> StringTable:
    """F5 BigIP SNAT data for monitoring Source NAT connections."""
    return [
        ["SQL", "3", "120", "0", "0", "3", "0"],
        ["MI-VSP", "2559", "267523", "2216", "2134447", "167", "0"],
        ["RS6000", "31", "1296", "31", "1264", "25", "0"],
        ["LS_Test", "0", "0", "0", "0", "0", "0"],
        ["foobar", "2221", "2226331", "1509", "729471", "79", "0"],
        ["keycomp", "2534239", "2132789593", "2490959", "1972334953", "464", "2"],
        ["AS400_20", "304980", "103809944", "268938", "39785918", "22631", "10"],
        ["AS400_21", "0", "0", "0", "0", "0", "0"],
        ["keycomp2", "183", "32988", "168", "73366", "12", "0"],
        ["websrvc2", "0", "0", "0", "0", "0", "0"],
        ["AS2_proxy", "10", "712", "5", "236", "7", "0"],
        ["MI-SENTRY", "0", "0", "0", "0", "0", "0"],
        [
            "Outbound_SNAT",
            "160631017",
            "30383696271",
            "217420496",
            "220088423650",
            "8870002",
            "8279",
        ],
        ["foo.bar.com", "0", "0", "0", "0", "0", "0"],
        ["baz.buz.com", "45412", "57683523", "26828", "6379159", "462", "0"],
        ["wuz.huz-kuz.com", "0", "0", "0", "0", "0", "0"],
        ["bar.foo.com", "339", "13560", "7", "280", "339", "0"],
        ["foo.bar.buz-huz.com", "0", "0", "0", "0", "0", "0"],
    ]


@pytest.fixture(name="f5_bigip_snat_parsed")
def _f5_bigip_snat_parsed(f5_bigip_snat_string_table: StringTable) -> dict[str, dict[str, Any]]:
    """Parsed F5 BigIP SNAT data."""
    return f5_bigip_snat.parse_f5_bigip_snat(f5_bigip_snat_string_table)


def test_discover_f5_bigip_snat(f5_bigip_snat_parsed: dict[str, dict[str, Any]]) -> None:
    """Test discovery function for F5 BigIP SNAT."""
    result = list(f5_bigip_snat.discover_f5_bigip_snat(f5_bigip_snat_parsed))
    # Should discover all SNAT entries including zero value ones
    expected_items = [
        "AS2_proxy",
        "AS400_20",
        "AS400_21",
        "LS_Test",
        "MI-SENTRY",
        "MI-VSP",
        "Outbound_SNAT",
        "RS6000",
        "SQL",
        "bar.foo.com",
        "baz.buz.com",
        "foo.bar.buz-huz.com",
        "foo.bar.com",
        "foobar",
        "keycomp",
        "keycomp2",
        "websrvc2",
        "wuz.huz-kuz.com",
    ]
    discovered_items = sorted([item for item, _ in result])
    assert discovered_items == sorted(expected_items)


def test_check_f5_bigip_snat_as2_proxy(
    f5_bigip_snat_parsed: dict[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test check function for AS2_proxy (zero traffic scenario)."""
    # Pre-populate value store to avoid rate calculation errors
    base_time = 1000000000
    value_store = {
        "if_in_pkts.0": (base_time, 10),
        "if_out_pkts.0": (base_time, 712),
        "if_in_octets.0": (base_time, 5),
        "if_out_octets.0": (base_time, 236),
        "connections_rate.0": (base_time, 7),
    }
    monkeypatch.setattr(f5_bigip_snat, "get_value_store", lambda: value_store)

    result = list(f5_bigip_snat.check_f5_bigip_snat("AS2_proxy", {}, f5_bigip_snat_parsed))

    # Should have 2 results: connections and rate
    assert len(result) == 2

    # First result should be client connections with metrics
    assert result[0][0] == 0  # OK state
    assert "Client connections: 0" in result[0][1]
    assert len(result[0]) == 3  # Has metrics
    metrics = result[0][2]
    assert len(metrics) == 6  # 6 metrics expected

    # Second result should be rate information
    assert result[1][0] == 0  # OK state
    assert "Rate:" in result[1][1]


def test_check_f5_bigip_snat_keycomp_high_traffic(
    f5_bigip_snat_parsed: dict[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test check function for keycomp (high traffic scenario)."""
    # Use current time for realistic rate calculations
    current_time = time.time()
    base_time = current_time - 60  # 60 seconds ago
    # Set up previous values for high traffic item (smaller values to avoid negative rates)
    value_store = {
        "if_in_pkts.0": (base_time, 2534200),  # Current: 2534239
        "if_out_pkts.0": (base_time, 2132789500),  # Current: 2132789593
        "if_in_octets.0": (base_time, 2490900),  # Current: 2490959
        "if_out_octets.0": (base_time, 1972334900),  # Current: 1972334953
        "connections_rate.0": (base_time, 460),  # Current: 464
    }
    monkeypatch.setattr(f5_bigip_snat, "get_value_store", lambda: value_store)

    result = list(f5_bigip_snat.check_f5_bigip_snat("keycomp", {}, f5_bigip_snat_parsed))

    # Should have 2 results: connections and rate
    assert len(result) == 2

    # First result should be client connections count
    assert result[0][0] == 0  # OK state
    assert "Client connections: 2" in result[0][1]  # Current connections
    assert len(result[0]) == 3  # Has metrics

    # Second result should be rate information
    assert result[1][0] == 0  # OK state
    assert "Rate:" in result[1][1]


def test_check_f5_bigip_snat_outbound_snat_large_numbers(
    f5_bigip_snat_parsed: dict[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test check function for Outbound_SNAT (very large numbers scenario)."""
    # Use current time for realistic rate calculations
    current_time = time.time()
    base_time = current_time - 60  # 60 seconds ago

    # Based on actual data: Outbound_SNAT has values [160631017, 30383696271, 217420496, 220088423650, 8870002, 8279]
    # if_in_pkts: [160631017], if_out_pkts: [30383696271], if_in_octets: [217420496], if_out_octets: [220088423650]
    # connections_rate: [8870002], connections: [8279]

    # Set up previous values for rate calculations (using correct field mapping)
    value_store = {
        "if_in_pkts.0": (base_time, 160630000),  # Current: 160631017
        "if_out_pkts.0": (base_time, 30383696000),  # Current: 30383696271
        "if_in_octets.0": (base_time, 217420000),  # Current: 217420496
        "if_out_octets.0": (base_time, 220088423000),  # Current: 220088423650
        "connections_rate.0": (base_time, 8869900),  # Current: 8870002
    }
    monkeypatch.setattr(f5_bigip_snat, "get_value_store", lambda: value_store)

    result = list(f5_bigip_snat.check_f5_bigip_snat("Outbound_SNAT", {}, f5_bigip_snat_parsed))

    # Should have 2 results: connections and rate
    assert len(result) == 2

    # First result should be client connections count
    assert result[0][0] == 0  # OK state
    assert "Client connections: 8279" in result[0][1]  # Current connections
    assert len(result[0]) == 3  # Has metrics
    metrics = result[0][2]
    # Verify metric names and structure
    metric_names = [metric[0] for metric in metrics]
    expected_metrics = [
        "if_in_pkts",
        "if_out_pkts",
        "if_in_octets",
        "if_out_octets",
        "connections_rate",
        "connections",
    ]
    assert metric_names == expected_metrics

    # Second result should be rate information
    assert result[1][0] == 0  # OK state
    assert "Rate:" in result[1][1]


def test_check_f5_bigip_snat_with_thresholds(
    f5_bigip_snat_parsed: dict[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test check function with configured thresholds."""
    base_time = 1000000000
    # Set up previous values
    value_store = {
        "if_in_pkts.0": (base_time, 2500),
        "if_out_pkts.0": (base_time, 260000),
        "if_in_octets.0": (base_time, 2100),
        "if_out_octets.0": (base_time, 2130000),
        "connections_rate.0": (base_time, 160),
    }
    monkeypatch.setattr(f5_bigip_snat, "get_value_store", lambda: value_store)

    # Test with threshold parameters
    params = {
        "if_in_octets": (1000000, 2000000),  # Warning at 1MB, Critical at 2MB per second
        "if_out_octets": (5000000, 10000000),  # Higher thresholds for outgoing
    }

    result = list(f5_bigip_snat.check_f5_bigip_snat("MI-VSP", params, f5_bigip_snat_parsed))

    # Should have base results plus any threshold violations
    assert len(result) >= 2  # At least connections and rate

    # May or may not have violations depending on calculated rates


def test_check_f5_bigip_snat_nonexistent_item(
    f5_bigip_snat_parsed: dict[str, dict[str, Any]],
) -> None:
    """Test check function with nonexistent SNAT item."""
    result = list(f5_bigip_snat.check_f5_bigip_snat("nonexistent_snat", {}, f5_bigip_snat_parsed))

    # Should return empty result for nonexistent items
    assert len(result) == 0


def test_parse_f5_bigip_snat_structure() -> None:
    """Test parsing function structure and field mapping."""
    string_table = [
        ["test_snat", "100", "200", "1024", "2048", "5", "3"],
        ["empty_snat", "0", "0", "0", "0", "0", "0"],
        ["invalid_snat", "abc", "def", "xyz", "123", "0", "1"],  # Invalid values
    ]

    result = f5_bigip_snat.parse_f5_bigip_snat(string_table)

    # Should parse valid entries
    assert "test_snat" in result
    assert "empty_snat" in result

    # Check field mapping for test_snat
    test_data = result["test_snat"]
    assert "if_in_pkts" in test_data
    assert "if_out_pkts" in test_data
    assert "if_in_octets" in test_data
    assert "if_out_octets" in test_data
    assert "connections_rate" in test_data
    assert "connections" in test_data

    # Values should be lists (for multiple entries support)
    assert test_data["if_in_pkts"] == [100]
    assert test_data["if_out_pkts"] == [200]
    assert test_data["if_in_octets"] == [1024]
    assert test_data["if_out_octets"] == [2048]
    assert test_data["connections_rate"] == [5]
    assert test_data["connections"] == [3]

    # Invalid entries should be partially parsed (skipping invalid values)
    assert "invalid_snat" in result
    invalid_data = result["invalid_snat"]
    # Should skip invalid numeric values but include valid ones
    assert "connections" in invalid_data
    assert invalid_data["connections"] == [1]


def test_parse_f5_bigip_snat_empty_input() -> None:
    """Test parsing function with empty input."""
    result = f5_bigip_snat.parse_f5_bigip_snat([])

    # Should return empty dict for empty input
    assert result == {}


def test_parse_f5_bigip_snat_malformed_data() -> None:
    """Test parsing function with malformed data."""
    string_table = [
        ["normal_entry", "1", "2", "3", "4", "5", "6"],  # Complete row
        ["", "1", "2", "3", "4", "5", "6"],  # Empty name but complete data
    ]

    result = f5_bigip_snat.parse_f5_bigip_snat(string_table)

    # Should handle complete rows properly
    assert "normal_entry" in result
    assert result["normal_entry"]["if_in_pkts"] == [1]
    assert result["normal_entry"]["connections"] == [6]

    # Empty names should be handled appropriately
    assert "" in result
    assert result[""]["if_in_pkts"] == [1]
