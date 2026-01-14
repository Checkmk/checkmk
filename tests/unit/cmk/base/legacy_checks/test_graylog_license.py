#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Tests for graylog_license legacy check."""

from typing import Any

from cmk.base.check_legacy_includes.graylog import parse_graylog_agent_data
from cmk.base.legacy_checks.graylog_license import (
    check_graylog_license,
    discover_graylog_license,
)


def test_discovery_graylog_license() -> None:
    """Test discovery function for graylog_license."""
    # Sample graylog license data
    info = [
        ['{"status": [{"valid": true, "expired": false, "violated": false}]}'],
    ]

    parsed = parse_graylog_agent_data(info)
    result = list(discover_graylog_license(parsed))

    # Should discover one item with None as the item name
    assert len(result) == 1
    assert result[0][0] is None


def test_check_graylog_license() -> None:
    """Test check function for graylog_license."""
    # Sample graylog license data with various status fields
    info = [
        [
            '{"status": [{"expired": false, "violated": false, "valid": true, "traffic_exceeded": false, "cluster_not_covered": false, "nodes_exceeded": false, "remote_checks_failed": false, "license": {"traffic_limit": 5368709120, "expiration_date": "2024-12-31T23:59:59Z", "subject": "/license/enterprise", "trial": false, "enterprise": {"require_remote_check": true}}}]}'
        ],
    ]

    parsed = parse_graylog_agent_data(info)
    params: dict[str, Any] = {}

    result = list(check_graylog_license(None, params, parsed))

    # Should return multiple results for license status checks
    assert len(result) >= 7  # At least the 7 main status checks

    # Check specific results - most are (state, summary) tuples
    result_summaries = [r[1] for r in result]  # Extract summary strings

    # Should include all the main status checks
    assert any("Is expired: no" in summary for summary in result_summaries)
    assert any("Is violated: no" in summary for summary in result_summaries)
    assert any("Is valid: yes" in summary for summary in result_summaries)
    assert any("Traffic is exceeded: no" in summary for summary in result_summaries)
    assert any("Cluster is not covered: no" in summary for summary in result_summaries)
    assert any("Nodes exceeded: no" in summary for summary in result_summaries)
    assert any("Remote checks failed: no" in summary for summary in result_summaries)

    # Should include license expiration information (this one has metrics)
    assert any("Expires in" in summary for summary in result_summaries)

    # Should include license subject and trial status
    assert any("Subject: /license/enterprise" in summary for summary in result_summaries)
    assert any("Trial: no" in summary for summary in result_summaries)

    # Should include remote check requirement
    assert any("Requires remote checks: yes" in summary for summary in result_summaries)


def test_check_graylog_license_no_enterprise() -> None:
    """Test check function when no enterprise license found."""
    # Sample data with empty status array (no enterprise license)
    info = [
        ['{"status": []}'],
    ]

    parsed = parse_graylog_agent_data(info)
    params: dict[str, Any] = {"no_enterprise": 1}

    result = list(check_graylog_license(None, params, parsed))

    # Should return single result about no enterprise license
    assert len(result) == 1
    state, summary = result[0]  # Simple (state, summary) tuple
    assert state == 1  # Warning state from params
    assert "No enterprise license found" in summary
