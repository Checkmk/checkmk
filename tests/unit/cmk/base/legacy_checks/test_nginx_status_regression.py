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

from cmk.base.legacy_checks.nginx_status import (
    check_nginx_status,
    discover_nginx_status,
    parse_nginx_status,
)

from .checktestlib import mock_item_state


def test_nginx_status_regression_discovery():
    """Test discovery of nginx status endpoints."""
    # Pattern 5d: System monitoring data (web server status)
    string_table = [
        ["127.0.0.1", "80", "Active", "connections:", "10"],
        ["127.0.0.1", "80", "serveracceptshandledrequests"],
        ["127.0.0.1", "80", "12", "10", "120"],
        ["127.0.0.1", "80", "Reading:", "2", "Writing:", "1", "Waiting:", "3"],
        ["127.0.1.1", "80", "Active", "connections:", "24"],
        ["127.0.1.1", "80", "server", "accepts", "handled", "requests"],
        ["127.0.1.1", "80", "23", "42", "323"],
        ["127.0.1.1", "80", "Reading:", "1", "Writing:", "5", "Waiting:", "0"],
    ]

    # Test discovery
    parsed = parse_nginx_status(string_table)
    discovery = list(discover_nginx_status(parsed))
    assert len(discovery) == 2
    items = [item for item, _params in discovery]
    assert "127.0.0.1:80" in items
    assert "127.0.1.1:80" in items


def test_nginx_status_regression_check():
    """Test nginx status check basic functionality."""
    # Pattern 5d: System monitoring data
    string_table = [
        ["127.0.0.1", "80", "Active", "connections:", "10"],
        ["127.0.0.1", "80", "serveracceptshandledrequests"],
        ["127.0.0.1", "80", "12", "10", "120"],
        ["127.0.0.1", "80", "Reading:", "2", "Writing:", "1", "Waiting:", "3"],
        ["127.0.1.1", "80", "Active", "connections:", "24"],
        ["127.0.1.1", "80", "server", "accepts", "handled", "requests"],
        ["127.0.1.1", "80", "23", "42", "323"],
        ["127.0.1.1", "80", "Reading:", "1", "Writing:", "5", "Waiting:", "0"],
    ]

    parsed = parse_nginx_status(string_table)

    # Mock item state with rate calculation history
    mock_state = {
        "nginx_status.accepted": (1570000000.0, 12),
        "nginx_status.handled": (1570000000.0, 10),
        "nginx_status.requests": (1570000000.0, 120),
    }

    with mock_item_state(mock_state):
        results = list(check_nginx_status("127.0.0.1:80", {}, parsed))

    # Should have results for active connections and rates
    assert len(results) >= 3
    # Check that active connections is reported
    assert any("Active:" in str(result) for result in results if len(result) > 1)


def test_nginx_status_regression_check_second_server():
    """Test nginx status check for second server basic functionality."""
    # Pattern 5d: System monitoring data
    string_table = [
        ["127.0.0.1", "80", "Active", "connections:", "10"],
        ["127.0.0.1", "80", "serveracceptshandledrequests"],
        ["127.0.0.1", "80", "12", "10", "120"],
        ["127.0.0.1", "80", "Reading:", "2", "Writing:", "1", "Waiting:", "3"],
        ["127.0.1.1", "80", "Active", "connections:", "24"],
        ["127.0.1.1", "80", "server", "accepts", "handled", "requests"],
        ["127.0.1.1", "80", "23", "42", "323"],
        ["127.0.1.1", "80", "Reading:", "1", "Writing:", "5", "Waiting:", "0"],
    ]

    parsed = parse_nginx_status(string_table)

    # Mock item state for second server
    mock_state = {
        "nginx_status.accepted": (1570000000.0, 23),
        "nginx_status.handled": (1570000000.0, 42),
        "nginx_status.requests": (1570000000.0, 323),
    }

    with mock_item_state(mock_state):
        results = list(check_nginx_status("127.0.1.1:80", {}, parsed))

    # Should have results for active connections and rates for second server
    assert len(results) >= 3
    # Check that active connections is reported for second server
    assert any("Active:" in str(result) for result in results if len(result) > 1)
