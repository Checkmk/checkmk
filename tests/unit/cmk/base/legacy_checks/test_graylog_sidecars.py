#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Tests for graylog_sidecars legacy check."""

from typing import Any

from cmk.base.legacy_checks.graylog_sidecars import (
    check_graylog_sidecars,
    discover_graylog_sidecars,
    parse_graylog_sidecars,
)


def test_discovery_graylog_sidecars() -> None:
    """Test discovery function for graylog_sidecars."""
    # Sample graylog sidecar data with node names
    string_table = [
        [
            '{"node_name": "test-node-1", "active": true, "last_seen": "2024-01-01T12:00:00.000Z", "node_details": {"status": {"status": 0, "message": "1 running/0 stopped/0 failing"}}}'
        ],
        [
            '{"node_name": "test-node-2", "active": false, "last_seen": "2024-01-01T11:00:00.000Z", "node_details": {"status": {"status": 1, "message": "0 running/1 stopped/0 failing"}}}'
        ],
    ]

    parsed = parse_graylog_sidecars(string_table)
    result = list(discover_graylog_sidecars(parsed))

    # Should discover items for each node name
    assert len(result) == 2
    discovered_items = [item for item, params in result]
    assert "test-node-1" in discovered_items
    assert "test-node-2" in discovered_items


def test_check_graylog_sidecars_active_node() -> None:
    """Test check function for active graylog sidecar."""
    string_table = [
        ['{"node_name": "test-node-1", "active": true, "last_seen": "2024-01-01T12:00:00.000Z"}'],
    ]

    parsed = parse_graylog_sidecars(string_table)
    params: dict[str, Any] = {}

    result = list(check_graylog_sidecars("test-node-1", params, parsed))

    # Should return multiple results
    assert len(result) >= 2

    result_summaries = [r[1] for r in result]

    # Should show active status
    assert any("Active: yes" in summary for summary in result_summaries)

    # Should show last seen information
    assert any("Last seen:" in summary for summary in result_summaries)


def test_check_graylog_sidecars_inactive_node() -> None:
    """Test check function for inactive graylog sidecar."""
    string_table = [
        ['{"node_name": "test-node-2", "active": false, "last_seen": "2024-01-01T11:00:00.000Z"}'],
    ]

    parsed = parse_graylog_sidecars(string_table)
    params: dict[str, Any] = {"active_state": 2}  # Critical when inactive

    result = list(check_graylog_sidecars("test-node-2", params, parsed))

    # Should return multiple results
    assert len(result) >= 2

    result_summaries = [r[1] for r in result]

    # Should show inactive status
    assert any("Active: no" in summary for summary in result_summaries)

    # Check that the first result (active status) has critical state
    active_result = next((r for r in result if "Active:" in r[1]), None)
    assert active_result is not None
    assert active_result[0] == 2  # Critical state


def test_check_graylog_sidecars_missing_item() -> None:
    """Test check function when item not found."""
    string_table = [
        ['{"node_name": "test-node-1", "active": true, "last_seen": "2024-01-01T12:00:00.000Z"}'],
    ]

    parsed = parse_graylog_sidecars(string_table)
    params: dict[str, Any] = {}

    result = list(check_graylog_sidecars("nonexistent-node", params, parsed))

    # Should return empty result for missing item
    assert len(result) == 0
