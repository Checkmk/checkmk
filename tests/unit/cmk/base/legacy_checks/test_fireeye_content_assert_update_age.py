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

import time
from unittest.mock import patch

from cmk.base.legacy_checks.fireeye_content import (
    check_fireeye_content,
    discover_fireeye_content,
    parse_fireeye_content,
    SecurityContent,
)


def parsed() -> SecurityContent:
    """Return parsed data from actual parse function."""
    return parse_fireeye_content([["456.180", "0", "2016/02/26 15:42:06"]])


def test_fireeye_content_discovery():
    """Test discovery function finds content service."""
    discovery_result = list(discover_fireeye_content(parsed()))
    assert discovery_result == [(None, {})]


def test_fireeye_content_discovery_no_data():
    """Test discovery with no data returns nothing."""
    # Empty SecurityContent (what parse function returns when no data)
    empty_section = parse_fireeye_content([])
    discovery_result = list(discover_fireeye_content(empty_section))
    assert discovery_result == []


def test_fireeye_content_check_failed_update():
    """Test content check with failed update status."""
    params = {"update_time_levels": (9000000, 10000000)}

    # Mock time.time() to return the frozen time from dataset (2017-07-16T08:21:00)
    frozen_timestamp = time.mktime(time.strptime("2017-07-16 08:21:00", "%Y-%m-%d %H:%M:%S"))

    with patch("time.time", return_value=frozen_timestamp):
        results = list(check_fireeye_content(None, params, parsed()))

    # Extract states and summaries
    states = [r[0] for r in results]
    summaries = [r[1] for r in results]

    # Should have: warning for failed update, OK for last update, critical for age, OK for version
    assert states == [1, 0, 2, 0]
    assert "Update: failed" in summaries[0]
    assert "Last update: 2016/02/26 15:42:06" in summaries[1]
    assert "Age:" in summaries[2] and "warn/crit" in summaries[2]
    assert "Security version: 456.180" in summaries[3]


def test_fireeye_content_check_ok_update():
    """Test content check with successful update."""
    # Create parsed data with successful update (status "1")
    ok_parsed = parse_fireeye_content([["456.180", "1", "2017/07/16 08:20:00"]])
    params = {"update_time_levels": (9000000, 10000000)}

    frozen_timestamp = time.mktime(time.strptime("2017-07-16 08:21:00", "%Y-%m-%d %H:%M:%S"))

    with patch("time.time", return_value=frozen_timestamp):
        results = list(check_fireeye_content(None, params, ok_parsed))

    states = [r[0] for r in results]
    summaries = [r[1] for r in results]

    # Should have: OK for last update, OK for age (recent), OK for version
    assert states == [0, 0, 0]
    assert "Last update: 2017/07/16 08:20:00" in summaries[0]
    assert "Age:" in summaries[1]
    assert "Security version: 456.180" in summaries[2]


def test_fireeye_content_check_no_update_time():
    """Test content check with invalid update time."""
    # Create parsed data with invalid timestamp
    invalid_parsed = parse_fireeye_content([["456.180", "1", "invalid_time"]])
    params = {"update_time_levels": (9000000, 10000000)}

    results = list(check_fireeye_content(None, params, invalid_parsed))

    states = [r[0] for r in results]
    summaries = [r[1] for r in results]

    # Should have: OK for last update, OK for never completed, OK for version
    assert states == [0, 0, 0]
    assert "Last update: invalid_time" in summaries[0]
    assert "update has never completed" in summaries[1]
    assert "Security version: 456.180" in summaries[2]


def test_fireeye_content_parse_function():
    """Test parse function handles SNMP data correctly."""
    raw_data = [["456.180", "0", "2016/02/26 15:42:06"]]
    parsed_result = parse_fireeye_content(raw_data)

    assert parsed_result.version == "456.180"
    assert parsed_result.update_status == "failed"
    assert parsed_result.update_time_str == "2016/02/26 15:42:06"
    assert parsed_result.update_time_seconds is not None


def test_fireeye_content_parse_function_empty():
    """Test parse function with empty data."""
    parsed_result = parse_fireeye_content([])
    assert parsed_result is None
