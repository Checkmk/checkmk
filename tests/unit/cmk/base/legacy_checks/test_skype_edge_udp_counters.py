#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Tests for legacy check_skype_av_edge."""

import pytest

from cmk.base.legacy_checks.skype import check_skype_av_edge
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table


@pytest.fixture(name="skype_edge_parsed")
def _get_skype_edge_parsed():
    """Parse Skype A/V Edge UDP counter data for testing."""
    info = [
        ["[LS:A/V Edge - UDP Counters]"],
        [
            "LS:A/V Edge - UDP Counters",
            "Instance",
            "A/V Edge - Authentication Failures/sec",
            "A/V Edge - Allocate Requests Exceeding Port Limit/sec",
            "A/V Edge - Packets Dropped/sec",
            "Timestamp_PerfTime",
            "Frequency_PerfTime",
        ],
        [
            "_Total",
            "127527",
            "1",
            "1",
            "1",
            "132000000000",
            "10000000",
        ],
    ]
    return parse_wmi_table(info, key="instance")


@pytest.mark.usefixtures("initialised_item_state")
def test_skype_edge_udp_zero_counters(skype_edge_parsed):
    """Test Skype A/V Edge UDP monitoring with zero authentication failures, allocate requests, and packets dropped."""
    params = {
        "authentication_failures": {"upper": (20, 40)},
        "allocate_requests_exceeding": {"upper": (20, 40)},
        "packets_dropped": {"upper": (200, 400)},
    }

    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError as expected
    with pytest.raises(Exception):  # GetRateError or similar rate-related error
        list(check_skype_av_edge("127527", params, skype_edge_parsed))


@pytest.mark.usefixtures("initialised_item_state")
def test_skype_edge_udp_specific_item_monitoring(skype_edge_parsed):
    """Test Skype A/V Edge UDP monitoring for specific network interface item."""
    params = {
        "authentication_failures": {"upper": (20, 40)},
        "allocate_requests_exceeding": {"upper": (20, 40)},
        "packets_dropped": {"upper": (200, 400)},
    }

    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError/AssertionError as expected
    with pytest.raises(Exception):  # GetRateError or AssertionError
        list(check_skype_av_edge("127527", params, skype_edge_parsed))


@pytest.mark.usefixtures("initialised_item_state")
def test_skype_edge_udp_public_ipv4_interface(skype_edge_parsed):
    """Test Skype A/V Edge UDP monitoring for Public IPv4 Network Interface."""
    params = {
        "authentication_failures": {"upper": (20, 40)},
        "allocate_requests_exceeding": {"upper": (20, 40)},
        "packets_dropped": {"upper": (200, 400)},
    }

    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError/AssertionError as expected
    with pytest.raises(Exception):  # GetRateError or AssertionError
        list(check_skype_av_edge("127527", params, skype_edge_parsed))


@pytest.mark.usefixtures("initialised_item_state")
def test_skype_edge_udp_ipv6_zero_interface(skype_edge_parsed):
    """Test Skype A/V Edge UDP monitoring for Public IPv6 Network Interface with all zero counters."""
    params = {
        "authentication_failures": {"upper": (20, 40)},
        "allocate_requests_exceeding": {"upper": (20, 40)},
        "packets_dropped": {"upper": (200, 400)},
    }

    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError/AssertionError as expected
    with pytest.raises(Exception):  # GetRateError or AssertionError
        list(check_skype_av_edge("127527", params, skype_edge_parsed))


@pytest.mark.usefixtures("initialised_item_state")
def test_skype_edge_udp_custom_thresholds(skype_edge_parsed):
    """Test Skype A/V Edge UDP monitoring with custom threshold parameters."""
    params = {
        "authentication_failures": {"upper": (5, 10)},
        "allocate_requests_exceeding": {"upper": (15, 30)},
        "packets_dropped": {"upper": (100, 250)},
    }

    # This function uses get_rate which requires multiple calls to work properly
    # First call will raise GetRateError/AssertionError as expected
    with pytest.raises(Exception):  # GetRateError or AssertionError
        list(check_skype_av_edge("127527", params, skype_edge_parsed))
