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

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks import f5_bigip_vserver


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, object] = {}
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: store)


@pytest.fixture(name="string_table")
def _string_table() -> list[list[str]]:
    return [
        [
            "VS_BM",
            "1",
            "1",
            "The virtual server is available",
            "\xac\x14\xcad",
            "38",
            "76766",
            "10744",
            "70981",
            "84431",
            "10961763",
            "83403367",
            "2535",
            "0",
            "0",
        ],
    ]


@pytest.fixture(name="parsed")
def _parsed(string_table: list[list[str]]) -> Mapping[str, Any]:
    return f5_bigip_vserver.parse_f5_bigip_vserver(string_table)


@pytest.mark.usefixtures("empty_value_store")
def test_parse_f5_bigip_vserver_division_regression(parsed: Mapping[str, Any]) -> None:
    assert "VS_BM" in parsed
    vs_data = parsed["VS_BM"]

    assert vs_data["status"] == "1"
    assert vs_data["enabled"] == "1"
    assert vs_data["detail"] == "The virtual server is available"
    assert vs_data["ip_address"] == "172.20.202.100"

    # Check that numeric values are parsed correctly with proper scaling
    assert vs_data["connections_duration_min"] == [0.038]  # 38 * 0.001
    assert vs_data["connections_duration_max"] == [76.766]  # 76766 * 0.001
    assert vs_data["connections_duration_mean"] == [10.744]  # 10744 * 0.001
    assert vs_data["if_in_pkts"] == [70981]
    assert vs_data["if_out_pkts"] == [84431]
    assert vs_data["if_in_octets"] == [10961763]
    assert vs_data["if_out_octets"] == [83403367]
    assert vs_data["connections_rate"] == [2535]
    assert vs_data["connections"] == [0]
    assert vs_data["packet_velocity_asic"] == [0]


def test_discover_f5_bigip_vserver_division_regression(parsed: Mapping[str, Any]) -> None:
    result = list(f5_bigip_vserver.discover_f5_bigip_vserver(parsed))
    assert result == [("VS_BM", {})]


def test_check_f5_bigip_vserver_division_regression_basic(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store to avoid rate calculation errors on first run
    value_store: dict[str, object] = {
        "connections_rate.0": (0, 2535),
        "if_in_pkts.0": (0, 70981),
        "if_out_pkts.0": (0, 84431),
        "if_in_octets.0": (0, 10961763),
        "if_out_octets.0": (0, 83403367),
        "packet_velocity_asic.0": (0, 0),
    }
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)

    result = list(f5_bigip_vserver.check_f5_bigip_vserver("VS_BM", {}, parsed))

    assert len(result) == 4

    # Check status messages
    assert result[0] == (0, "Virtual Server with IP 172.20.202.100 is enabled")
    assert result[1] == (0, "State is up and available, Detail: The virtual server is available")

    # Check connections result with performance data
    state, summary, metrics = result[2]
    assert state == 0
    assert summary == "Client connections: 0"

    # The metrics are in key-value pairs from sorted(aggregation.items())
    # So we get [('connections', 0), ('connections_duration_max', 76.766), ...]
    assert len(metrics) == 12  # All performance metrics

    # Convert to dict for easier verification
    metric_dict = dict(metrics)
    assert metric_dict["connections"] == 0
    assert metric_dict["connections_duration_max"] == 76.766
    assert metric_dict["connections_duration_mean"] == 10.744
    assert metric_dict["connections_duration_min"] == 0.038
    assert metric_dict["connections_rate"] == 0.0
    assert metric_dict["if_in_octets"] == 0.0
    assert metric_dict["if_in_pkts"] == 0.0
    assert metric_dict["if_out_octets"] == 0.0
    assert metric_dict["if_out_pkts"] == 0.0

    # Check connections rate message
    assert result[3] == (0, "Connections rate: 0.00/sec")


@pytest.mark.usefixtures("empty_value_store")
def test_check_f5_bigip_vserver_division_regression_missing_item(parsed: Mapping[str, Any]) -> None:
    result = list(f5_bigip_vserver.check_f5_bigip_vserver("NonExistent", {}, parsed))
    assert result == []


def test_check_f5_bigip_vserver_division_regression_with_params(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store
    value_store: dict[str, object] = {
        "connections_rate.0": (0, 2535),
        "if_in_pkts.0": (0, 70981),
        "if_out_pkts.0": (0, 84431),
        "if_in_octets.0": (0, 10961763),
        "if_out_octets.0": (0, 83403367),
        "packet_velocity_asic.0": (0, 0),
    }
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)

    params = {
        "connections": (50, 100),  # warn, crit thresholds
        "state": {"is_up_and_available": 0},
    }

    result = list(f5_bigip_vserver.check_f5_bigip_vserver("VS_BM", params, parsed))

    assert len(result) == 4

    # Verify that connection thresholds are handled (current connections = 0, below warn threshold)
    state, summary, metrics = result[2]
    assert state == 0  # OK state since 0 < 50 (warn threshold)
    assert "Client connections: 0" in summary


@pytest.mark.usefixtures("empty_value_store")
def test_check_f5_bigip_vserver_division_regression_disabled(string_table: list[list[str]]) -> None:
    # Modify string table to have a disabled virtual server
    disabled_string_table = [
        [
            "VS_DISABLED",
            "0",  # status: disabled
            "0",  # enabled: NONE
            "Virtual server is disabled",
            "\xac\x14\xcad",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
        ],
    ]

    parsed = f5_bigip_vserver.parse_f5_bigip_vserver(disabled_string_table)
    result = list(f5_bigip_vserver.check_f5_bigip_vserver("VS_DISABLED", {}, parsed))

    # Should have at least the status check
    assert len(result) >= 2
    assert result[0][0] == 0  # OK state for enabled state (even if NONE, it's in MAP_ENABLED)
    assert "NONE" in result[0][1]
    assert result[1][0] == 1  # Warning state for disabled status
    assert "is disabled" in result[1][1]
