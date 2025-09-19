#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.cisco_prime_wifi_access_points import (
    check_cisco_prime_wifi_access_points,
    discover_cisco_prime_wifi_access_points,
    parse_cisco_prime_wifi_access_points,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for Cisco Prime WiFi access points"""
    return [
        [
            """
{
  "queryResponse": {
    "entity": [
      {
        "@dtoType": "accessPointsDTO",
        "@type": "AccessPoints",
        "@url": "https://example.com/webacs/api/v1/data/AccessPoints/2101795",
        "accessPointsDTO": {
          "@displayName": "2101795",
          "@id": "2101795",
          "adminStatus": "ENABLE",
          "clientCount": 0,
          "clientCount_2_4GHz": 0,
          "clientCount_5GHz": 0,
          "controllerName": "wism22",
          "countryCode": "DE",
          "hreapEnabled": false,
          "location": "default location",
          "lwappUpTime": 70343302,
          "model": "AIR-LAP1131AG-E-K9",
          "softwareVersion": "8.0.152.12",
          "status": "CLEARED",
          "type": "AP1130",
          "upTime": 125852602
        }
      },
      {
        "@dtoType": "accessPointsDTO",
        "@type": "AccessPoints",
        "@url": "https://example.com/webacs/api/v1/data/AccessPoints/40164274",
        "accessPointsDTO": {
          "@displayName": "40164274",
          "@id": "40164274",
          "adminStatus": "ENABLE",
          "clientCount": 5,
          "clientCount_2_4GHz": 2,
          "clientCount_5GHz": 3,
          "controllerName": "wism23",
          "countryCode": "DE",
          "hreapEnabled": false,
          "location": "office location",
          "lwappUpTime": 80343302,
          "model": "AIR-LAP1142N-E-K9",
          "softwareVersion": "8.0.152.15",
          "status": "CRITICAL",
          "type": "AP1142N",
          "upTime": 135852602
        }
      },
      {
        "@dtoType": "accessPointsDTO",
        "@type": "AccessPoints",
        "@url": "https://example.com/webacs/api/v1/data/AccessPoints/50164275",
        "accessPointsDTO": {
          "@displayName": "50164275",
          "@id": "50164275",
          "adminStatus": "ENABLE",
          "clientCount": 10,
          "clientCount_2_4GHz": 4,
          "clientCount_5GHz": 6,
          "controllerName": "wism24",
          "countryCode": "DE",
          "hreapEnabled": true,
          "location": "warehouse location",
          "lwappUpTime": 90343302,
          "model": "AIR-LAP1252AG-E-K9",
          "softwareVersion": "8.0.152.20",
          "status": "CLEARED",
          "type": "AP1252",
          "upTime": 145852602
        }
      }
    ]
  }
}
"""
        ]
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> Mapping[str, Any]:
    """Parsed Cisco Prime WiFi access points data"""
    return parse_cisco_prime_wifi_access_points(string_table)


def test_parse_cisco_prime_wifi_access_points(string_table: list[list[str]]) -> None:
    """Test Cisco Prime WiFi access points parsing extracts correct data"""
    parsed = parse_cisco_prime_wifi_access_points(string_table)

    # Should have 3 access points
    assert len(parsed) == 3

    # Check specific access point data
    assert "2101795" in parsed
    assert "40164274" in parsed
    assert "50164275" in parsed

    # Check data structure
    ap1 = parsed["2101795"]
    assert ap1["@displayName"] == "2101795"
    assert ap1["status"] == "CLEARED"
    assert ap1["model"] == "AIR-LAP1131AG-E-K9"
    assert ap1["clientCount"] == 0

    ap2 = parsed["40164274"]
    assert ap2["@displayName"] == "40164274"
    assert ap2["status"] == "CRITICAL"
    assert ap2["model"] == "AIR-LAP1142N-E-K9"
    assert ap2["clientCount"] == 5


def test_parse_cisco_prime_wifi_access_points_empty() -> None:
    """Test parsing with empty query response"""
    empty_data = [['{"queryResponse": {"entity": []}}']]
    parsed = parse_cisco_prime_wifi_access_points(empty_data)
    assert len(parsed) == 0


def test_discover_cisco_prime_wifi_access_points(parsed: dict[str, Any]) -> None:
    """Test Cisco Prime WiFi access points discovery"""
    discovered = list(discover_cisco_prime_wifi_access_points(parsed))

    # Should discover one service (aggregate check)
    assert len(discovered) == 1
    assert discovered[0] == (None, {})


def test_discover_cisco_prime_wifi_access_points_empty() -> None:
    """Test discovery with empty data"""
    discovered = list(discover_cisco_prime_wifi_access_points({}))
    assert len(discovered) == 0


def test_check_cisco_prime_wifi_access_points_normal(parsed: dict[str, Any]) -> None:
    """Test Cisco Prime WiFi access points check with normal thresholds"""
    params = {"levels": (20.0, 40.0)}

    result = list(check_cisco_prime_wifi_access_points(None, params, parsed))

    # Should have percentage check + status counts
    assert len(result) >= 2

    # First result should be the percentage critical check
    percent_result = result[0]
    assert percent_result[0] == 1  # WARNING state (33.3% critical >= 20% threshold)
    assert "Percent Critical" in percent_result[1]
    assert "33.33%" in percent_result[1]  # 1 critical out of 3 total = 33.3%

    # Check performance data
    perf_data = percent_result[2]
    assert len(perf_data) == 1
    assert perf_data[0][0] == "ap_devices_percent_unhealthy"
    assert abs(perf_data[0][1] - 33.333333) < 0.001  # 1/3 * 100

    # Check status counts in remaining results
    status_results = result[1:]
    status_texts = [res[1] for res in status_results]
    status_text = " ".join(status_texts)

    assert "Cleared: 2" in status_text
    assert "Critical: 1" in status_text


def test_check_cisco_prime_wifi_access_points_warning_threshold() -> None:
    """Test Cisco Prime WiFi access points check with warning threshold exceeded"""
    test_data = {
        "1": {"status": "CLEARED"},
        "2": {"status": "CRITICAL"},
        "3": {"status": "CRITICAL"},
        "4": {"status": "CLEARED"},
    }

    params = {"levels": (40.0, 60.0)}  # 50% critical should trigger warning

    result = list(check_cisco_prime_wifi_access_points(None, params, test_data))

    # First result should be WARNING (50% critical >= 40% warning threshold)
    percent_result = result[0]
    assert percent_result[0] == 1  # WARNING state
    assert "Percent Critical" in percent_result[1]
    assert "50.00%" in percent_result[1]


def test_check_cisco_prime_wifi_access_points_critical_threshold() -> None:
    """Test Cisco Prime WiFi access points check with critical threshold exceeded"""
    test_data = {
        "1": {"status": "CRITICAL"},
        "2": {"status": "CRITICAL"},
        "3": {"status": "CRITICAL"},
        "4": {"status": "CLEARED"},
    }

    params = {"levels": (20.0, 40.0)}  # 75% critical should trigger critical

    result = list(check_cisco_prime_wifi_access_points(None, params, test_data))

    # First result should be CRITICAL (75% critical >= 40% critical threshold)
    percent_result = result[0]
    assert percent_result[0] == 2  # CRITICAL state
    assert "Percent Critical" in percent_result[1]
    assert "75.00%" in percent_result[1]


def test_check_cisco_prime_wifi_access_points_no_thresholds() -> None:
    """Test Cisco Prime WiFi access points check with no thresholds configured"""
    test_data = {
        "1": {"status": "CLEARED"},
        "2": {"status": "CRITICAL"},
    }

    params = {"levels": (None, None)}

    result = list(check_cisco_prime_wifi_access_points(None, params, test_data))

    # Should always be OK when no thresholds are set
    percent_result = result[0]
    assert percent_result[0] == 0  # OK state
    assert "Percent Critical" in percent_result[1]
    assert "50.00%" in percent_result[1]


def test_check_cisco_prime_wifi_access_points_various_statuses() -> None:
    """Test Cisco Prime WiFi access points check with various status types"""
    test_data = {
        "1": {"status": "CLEARED"},
        "2": {"status": "CRITICAL"},
        "3": {"status": "WARNING"},
        "4": {"status": "MAJOR"},
        "5": {"status": "MINOR"},
        "6": {"status": "INFO"},
    }

    params = {"levels": (20.0, 40.0)}

    result = list(check_cisco_prime_wifi_access_points(None, params, test_data))

    # Should count each status type
    status_results = result[1:]
    status_performance_data = []
    for res in status_results:
        if len(res) == 3 and res[2]:  # Has performance data
            status_performance_data.extend(res[2])

    # Check that all status types are counted
    perf_metrics = [perf[0] for perf in status_performance_data]
    assert "ap_devices_cleared" in perf_metrics
    assert "ap_devices_critical" in perf_metrics
    assert "ap_devices_warning" in perf_metrics
    assert "ap_devices_major" in perf_metrics
    assert "ap_devices_minor" in perf_metrics
    assert "ap_devices_info" in perf_metrics


def test_check_cisco_prime_wifi_access_points_all_healthy() -> None:
    """Test Cisco Prime WiFi access points check with all devices healthy"""
    test_data = {
        "1": {"status": "CLEARED"},
        "2": {"status": "CLEARED"},
        "3": {"status": "CLEARED"},
    }

    params = {"levels": (20.0, 40.0)}

    result = list(check_cisco_prime_wifi_access_points(None, params, test_data))

    # Should have 0% critical
    percent_result = result[0]
    assert percent_result[0] == 0  # OK state
    assert "0%" in percent_result[1]

    # Should only show cleared count
    status_results = result[1:]
    assert len(status_results) == 1
    assert "Cleared: 3" in status_results[0][1]


def test_check_cisco_prime_wifi_access_points_all_critical() -> None:
    """Test Cisco Prime WiFi access points check with all devices critical"""
    test_data = {
        "1": {"status": "CRITICAL"},
        "2": {"status": "CRITICAL"},
    }

    params = {"levels": (20.0, 40.0)}

    result = list(check_cisco_prime_wifi_access_points(None, params, test_data))

    # Should have 100% critical
    percent_result = result[0]
    assert percent_result[0] == 2  # CRITICAL state
    assert "100.00%" in percent_result[1]

    # Should only show critical count
    status_results = result[1:]
    assert len(status_results) == 1
    assert "Critical: 2" in status_results[0][1]
