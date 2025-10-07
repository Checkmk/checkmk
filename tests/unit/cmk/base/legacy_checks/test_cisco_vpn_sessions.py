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

from cmk.base.legacy_checks.cisco_vpn_sessions import (
    check_cisco_vpn_sessions,
    discover_cisco_vpn_sessions,
)
from cmk.plugins.collection.agent_based.cisco_vpn_sessions import parse_cisco_vpn_sessions


def parsed() -> Mapping[str, Any]:
    """Return parsed data from actual parse function."""
    section = parse_cisco_vpn_sessions(
        [["31", "100", "50", "2", "55", "11", "776", "10000", "800", "0", "0", "0", "12345"]]
    )
    assert section
    return section


def test_cisco_vpn_sessions_discovery() -> None:
    assert list(discover_cisco_vpn_sessions(parsed())) == [
        ("IPsec RA", {}),
        ("IPsec L2L", {}),
        ("AnyConnect SVC", {}),
        ("WebVPN", {}),
        ("Summary", {}),
    ]


def test_cisco_vpn_sessions_check_ipsec_ra() -> None:
    """Test check function for IPsec RA sessions."""
    params = {"active_sessions": (10, 100)}

    results = list(check_cisco_vpn_sessions("IPsec RA", params, parsed()))

    # Should have active sessions check with warning (31 > 10)
    assert len(results) >= 2

    # Handle variable result tuple formats
    for result in results:
        if len(result) == 2:
            state, summary = result
        elif len(result) == 3:
            state, summary, metrics = result
        else:
            assert False, f"Unexpected result format: {result}"

    # First result should be active sessions with warning
    first_result = results[0]
    assert first_result[0] == 1  # Warning state
    assert "Active sessions: 31" in first_result[1]


def test_cisco_vpn_sessions_check_l2l() -> None:
    """Test check function for IPsec L2L sessions."""
    params = {"active_sessions": (10, 100)}

    results = list(check_cisco_vpn_sessions("IPsec L2L", params, parsed()))

    # Should have results for L2L sessions (2 sessions, under threshold)
    assert len(results) >= 2

    # Handle variable result tuple formats
    for result in results:
        if len(result) == 2:
            state, summary = result
        elif len(result) == 3:
            state, summary, metrics = result
        else:
            assert False, f"Unexpected result format: {result}"

    # First result should be active sessions, no warning (2 < 10)
    first_result = results[0]
    assert first_result[0] == 0  # OK state
    assert "Active sessions: 2" in first_result[1]


def test_cisco_vpn_sessions_check_summary() -> None:
    """Test check function for Summary (different behavior)."""
    results = list(check_cisco_vpn_sessions("Summary", {}, parsed()))

    # Summary has different behavior (no peak count)
    assert len(results) >= 1

    # Handle variable result tuple formats
    for result in results:
        if len(result) == 2:
            state, summary = result
        elif len(result) == 3:
            state, summary, metrics = result
        else:
            assert False, f"Unexpected result format: {result}"


def test_cisco_vpn_sessions_check_missing_item() -> None:
    """Test check function with non-existent item."""
    results = list(check_cisco_vpn_sessions("Missing Item", {}, parsed()))

    # Should return empty results for missing item
    assert len(results) == 0


def test_cisco_vpn_sessions_parse_function() -> None:
    """Test that parse function creates expected data structure."""
    section = parsed()

    # Should have all VPN session types
    assert "IPsec RA" in section
    assert "IPsec L2L" in section
    assert "AnyConnect SVC" in section
    assert "WebVPN" in section
    assert "Summary" in section

    # Check IPsec RA data structure
    ipsec_ra = section["IPsec RA"]
    assert "active_sessions" in ipsec_ra
    assert ipsec_ra["active_sessions"] == 31
    assert "peak_sessions" in ipsec_ra
    assert ipsec_ra["peak_sessions"] == 50

    # Check L2L data
    l2l = section["IPsec L2L"]
    assert l2l["active_sessions"] == 2
    assert l2l["peak_sessions"] == 11
