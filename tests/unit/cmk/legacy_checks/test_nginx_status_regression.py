#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.agent_based.v2 import Result, Service
from cmk.legacy_checks.nginx_status import (
    check_nginx_status,
    discover_nginx_status,
    parse_nginx_status,
)

from .checktestlib import mock_item_state


def test_nginx_status_regression_discovery() -> None:
    """Test discovery of nginx status endpoints."""
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
    discovery = list(discover_nginx_status(parsed))
    assert len(discovery) == 2
    items = [s.item for s in discovery]
    assert "127.0.0.1:80" in items
    assert "127.0.1.1:80" in items
    for s in discovery:
        assert isinstance(s, Service)


def test_nginx_status_regression_check() -> None:
    """Test nginx status check basic functionality."""
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

    mock_state = {
        "nginx_status.accepted": (1570000000.0, 12),
        "nginx_status.handled": (1570000000.0, 10),
        "nginx_status.requests": (1570000000.0, 120),
    }

    with mock_item_state(mock_state):
        results = list(check_nginx_status("127.0.0.1:80", {}, parsed))

    assert len(results) >= 3
    assert any(isinstance(r, Result) and "Active:" in r.summary for r in results)


def test_nginx_status_regression_check_second_server() -> None:
    """Test nginx status check for second server basic functionality."""
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

    mock_state = {
        "nginx_status.accepted": (1570000000.0, 23),
        "nginx_status.handled": (1570000000.0, 42),
        "nginx_status.requests": (1570000000.0, 323),
    }

    with mock_item_state(mock_state):
        results = list(check_nginx_status("127.0.1.1:80", {}, parsed))

    assert len(results) >= 3
    assert any(isinstance(r, Result) and "Active:" in r.summary for r in results)
