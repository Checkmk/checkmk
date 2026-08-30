#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import time
from unittest.mock import patch

from cmk.agent_based.v2 import Result, Service, State
from cmk.legacy_checks.fireeye_content import (
    check_fireeye_content,
    discover_fireeye_content,
    parse_fireeye_content,
    SecurityContent,
)


def parsed() -> SecurityContent:
    """Return parsed data from actual parse function."""
    section = parse_fireeye_content([["456.180", "0", "2016/02/26 15:42:06"]])
    assert section is not None
    return section


def test_fireeye_content_discovery() -> None:
    """Test discovery function finds content service."""
    assert list(discover_fireeye_content(parsed())) == [Service()]


def test_fireeye_content_check_failed_update() -> None:
    """Test content check with failed update status."""
    params = {"update_time_levels": (9000000.0, 10000000.0)}

    # Mock time.time() to return the frozen time from dataset (2017-07-16T08:21:00)
    frozen_timestamp = time.mktime(time.strptime("2017-07-16 08:21:00", "%Y-%m-%d %H:%M:%S"))

    with patch("time.time", return_value=frozen_timestamp):
        results = [r for r in check_fireeye_content(params, parsed()) if isinstance(r, Result)]

    # Should have: warning for failed update, OK for last update, critical for age, OK for version
    assert [r.state for r in results] == [State.WARN, State.OK, State.CRIT, State.OK]
    summaries = [r.summary for r in results]
    assert "Update: failed" in summaries[0]
    assert "Last update: 2016/02/26 15:42:06" in summaries[1]
    assert "Age:" in summaries[2] and "warn/crit" in summaries[2]
    assert "Security version: 456.180" in summaries[3]


def test_fireeye_content_check_ok_update() -> None:
    """Test content check with successful update."""
    # Create parsed data with successful update (status "1")
    ok_parsed = parse_fireeye_content([["456.180", "1", "2017/07/16 08:20:00"]])
    assert ok_parsed is not None
    params = {"update_time_levels": (9000000.0, 10000000.0)}

    frozen_timestamp = time.mktime(time.strptime("2017-07-16 08:21:00", "%Y-%m-%d %H:%M:%S"))

    with patch("time.time", return_value=frozen_timestamp):
        results = [r for r in check_fireeye_content(params, ok_parsed) if isinstance(r, Result)]

    # Should have: OK for last update, OK for age (recent), OK for version
    assert [r.state for r in results] == [State.OK, State.OK, State.OK]
    summaries = [r.summary for r in results]
    assert "Last update: 2017/07/16 08:20:00" in summaries[0]
    assert "Age:" in summaries[1]
    assert "Security version: 456.180" in summaries[2]


def test_fireeye_content_check_no_update_time() -> None:
    """Test content check with invalid update time."""
    # Create parsed data with invalid timestamp
    invalid_parsed = parse_fireeye_content([["456.180", "1", "invalid_time"]])
    assert invalid_parsed is not None
    params = {"update_time_levels": (9000000.0, 10000000.0)}

    results = [r for r in check_fireeye_content(params, invalid_parsed) if isinstance(r, Result)]

    # Should have: OK for last update, OK for never completed, OK for version
    assert [r.state for r in results] == [State.OK, State.OK, State.OK]
    summaries = [r.summary for r in results]
    assert "Last update: invalid_time" in summaries[0]
    assert "update has never completed" in summaries[1]
    assert "Security version: 456.180" in summaries[2]


def test_fireeye_content_parse_function() -> None:
    """Test parse function handles SNMP data correctly."""
    parsed_result = parse_fireeye_content([["456.180", "0", "2016/02/26 15:42:06"]])

    assert parsed_result is not None
    assert parsed_result.version == "456.180"
    assert parsed_result.update_status == "failed"
    assert parsed_result.update_time_str == "2016/02/26 15:42:06"
    assert parsed_result.update_time_seconds is not None


def test_fireeye_content_parse_function_empty() -> None:
    """Test parse function with empty data."""
    assert parse_fireeye_content([]) is None
