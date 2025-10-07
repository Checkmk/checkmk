#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from unittest.mock import patch

from cmk.base.legacy_checks.fireeye_content import (
    check_fireeye_content,
    discover_fireeye_content,
    parse_fireeye_content,
)


def test_fireeye_content_update_failed_discovery():
    """Test discovery of FireEye content status when update failed."""
    # SNMP data: [version, status, timestamp] - status "0" means failed
    string_table = [["456.180", "0", "2016/02/26 15:42:06"]]
    parsed = parse_fireeye_content(string_table)

    # Test discovery
    discovery = list(discover_fireeye_content(parsed))
    assert discovery == [(None, {})]


def test_fireeye_content_update_failed():
    """Test FireEye content check with failed update."""
    # SNMP data: [version, status, timestamp] - status "0" means failed
    string_table = [["456.180", "0", "2016/02/26 15:42:06"]]
    parsed = parse_fireeye_content(string_table)

    # Freeze time to match expected age calculation
    with patch("time.time", return_value=1468656060.0):  # 2017-07-16T08:21:00
        results = list(check_fireeye_content(None, {}, parsed))

    # Check the structure and key messages
    assert len(results) == 4
    assert results[0] == (1, "Update: failed")  # First message is the failure
    assert results[1][1] == "Last update: 2016/02/26 15:42:06"
    assert "Age:" in results[2][1]
    assert results[3][1] == "Security version: 456.180"
