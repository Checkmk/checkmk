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


@pytest.fixture(name="string_table")
def _string_table() -> list[list[str]]:
    return [
        [
            "/Common/sight-seeing.wurmhole.univ",
            "1",
            "1",
            "The virtual server is available",
            "\xd4;xK",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "0",
            "",
        ],
        [
            "/Common/www.wurmhole.univ_HTTP2HTTPS",
            "4",
            "1",
            (
                "The children pool member(s) either don't"
                " have service checking enabled, or service check results are not available yet"
            ),
            "\xd4;xI",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "42",
            "0",
            "",
        ],
        [
            "/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS",
            "4",
            "1",
            (
                "The children pool member(s) either"
                " don't have service checking enabled, or service check results are not available yet"
            ),
            "\xd4;xK",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "0",
            "",
        ],
        [
            "/Common/starfleet.space",
            "4",
            "",
            "To infinity and beyond!",
            "\xde\xca\xff\xed",
            "",
            "",
            "",
            "",
            "42",
            "32",
            "",
            "",
            "0",
            "",
        ],
    ]


@pytest.fixture(name="parsed")
def _parsed(string_table: list[list[str]]) -> Mapping[str, Any]:
    return f5_bigip_vserver.parse_f5_bigip_vserver(string_table)


def test_parse_f5_bigip_vserver_regression(parsed: Mapping[str, Any]) -> None:
    assert len(parsed) == 4

    # Check available virtual server
    vs_available = parsed["/Common/sight-seeing.wurmhole.univ"]
    assert vs_available["status"] == "1"  # available
    assert vs_available["enabled"] == "1"  # enabled
    assert vs_available["detail"] == "The virtual server is available"
    assert vs_available["ip_address"] == "212.59.120.75"

    # Check unknown state virtual server with connections_rate
    vs_unknown_with_rate = parsed["/Common/www.wurmhole.univ_HTTP2HTTPS"]
    assert vs_unknown_with_rate["status"] == "4"  # unknown availability
    assert vs_unknown_with_rate["enabled"] == "1"  # enabled
    assert vs_unknown_with_rate["ip_address"] == "212.59.120.73"
    assert vs_unknown_with_rate["connections_rate"] == [42]

    # Check starfleet.space with in/out traffic
    vs_starfleet = parsed["/Common/starfleet.space"]
    assert vs_starfleet["status"] == "4"  # unknown availability
    assert vs_starfleet["enabled"] == ""  # empty enabled state (unknown)
    assert vs_starfleet["detail"] == "To infinity and beyond!"
    assert vs_starfleet["ip_address"] == "222.202.255.237"
    assert vs_starfleet["if_out_pkts"] == [42]
    assert vs_starfleet["if_in_octets"] == [32]


def test_discover_f5_bigip_vserver_regression(parsed: Mapping[str, Any]) -> None:
    result = list(f5_bigip_vserver.discover_f5_bigip_vserver(parsed))

    expected_items = [
        "/Common/sight-seeing.wurmhole.univ",
        "/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS",
        "/Common/www.wurmhole.univ_HTTP2HTTPS",
        "/Common/starfleet.space",
    ]

    assert len(result) == 4
    for item_name, params in result:
        assert item_name in expected_items
        assert params == {}


def test_check_f5_bigip_vserver_regression_unknown_state(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store for items that need it
    value_store: dict[str, object] = {"connections_rate.0": (0, 42)}
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)

    result = list(
        f5_bigip_vserver.check_f5_bigip_vserver(
            "/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS", {}, parsed
        )
    )

    assert len(result) == 3

    # Check status messages
    assert result[0] == (0, "Virtual Server with IP 212.59.120.75 is enabled")
    assert result[1][0] == 1  # Warning state for unknown availability
    assert "State availability is unknown" in result[1][1]
    assert "children pool member(s)" in result[1][1]

    # Check connections result
    state, summary, metrics = result[2]
    assert state == 0
    assert summary == "Client connections: 0"

    # Convert metrics to dict
    metric_dict = dict(metrics)
    assert metric_dict["connections"] == 0


def test_check_f5_bigip_vserver_regression_with_rate(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pre-populate value store for rate calculations
    value_store: dict[str, object] = {"connections_rate.0": (0, 42)}
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)

    result = list(
        f5_bigip_vserver.check_f5_bigip_vserver("/Common/www.wurmhole.univ_HTTP2HTTPS", {}, parsed)
    )

    assert len(result) == 4

    # Check status messages
    assert result[0] == (0, "Virtual Server with IP 212.59.120.73 is enabled")
    assert result[1][0] == 1  # Warning state for unknown availability

    # Check connections result with rate metrics
    state, summary, metrics = result[2]
    assert state == 0
    assert summary == "Client connections: 0"

    # Convert metrics to dict
    metric_dict = dict(metrics)
    assert metric_dict["connections"] == 0
    assert metric_dict["connections_rate"] == 0

    # Check connections rate message
    assert result[3] == (0, "Connections rate: 0.00/sec")


def test_check_f5_bigip_vserver_regression_missing_item(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test item that was discovered but doesn't produce any check results
    value_store: dict[str, object] = {}
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)
    result = list(f5_bigip_vserver.check_f5_bigip_vserver("/Common/www.wurmhole.univ", {}, parsed))
    assert result == []


def test_check_f5_bigip_vserver_regression_unknown_enabled_state(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test starfleet.space which has empty enabled state (unknown)
    value_store: dict[str, object] = {"if_out_pkts.0": (0, 42), "if_in_octets.0": (0, 32)}
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)

    result = list(f5_bigip_vserver.check_f5_bigip_vserver("/Common/starfleet.space", {}, parsed))

    assert len(result) >= 3

    # Check enabled state - empty string not in MAP_ENABLED, so should be warning
    assert result[0][0] == 1  # Warning state for unknown enabled state
    assert "in unknown state" in result[0][1]
    assert "222.202.255.237" in result[0][1]

    # Check status state - availability is unknown
    assert result[1][0] == 1  # Warning state for unknown availability
    assert "availability is unknown" in result[1][1]
    assert "To infinity and beyond!" in result[1][1]


def test_check_f5_bigip_vserver_regression_with_thresholds(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test starfleet.space with threshold parameters
    value_store: dict[str, object] = {"if_out_pkts.0": (0, 42), "if_in_octets.0": (0, 32)}
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)

    params = {
        "if_in_octets": (-23, 42),
        "if_total_pkts_lower": (100, 200),
        "if_total_pkts": (300, 400),
    }

    result = list(
        f5_bigip_vserver.check_f5_bigip_vserver("/Common/starfleet.space", params, parsed)
    )

    assert len(result) >= 5

    # Should have threshold-based checks that return non-OK states
    states = [r[0] for r in result]
    assert 1 in states  # Warning for incoming bytes threshold
    assert 2 in states  # Critical for total packets threshold

    # Check that we have threshold-related messages
    messages = [r[1] for r in result]
    threshold_messages = [msg for msg in messages if "warn/crit" in msg]
    assert len(threshold_messages) >= 2  # At least 2 threshold checks


def test_check_f5_bigip_vserver_regression_available_basic(
    parsed: Mapping[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test the basic available virtual server
    value_store: dict[str, object] = {}
    monkeypatch.setattr(f5_bigip_vserver, "get_value_store", lambda: value_store)
    result = list(
        f5_bigip_vserver.check_f5_bigip_vserver("/Common/sight-seeing.wurmhole.univ", {}, parsed)
    )

    assert len(result) >= 2

    # Check status messages
    assert result[0] == (0, "Virtual Server with IP 212.59.120.75 is enabled")
    assert result[1] == (0, "State is up and available, Detail: The virtual server is available")
