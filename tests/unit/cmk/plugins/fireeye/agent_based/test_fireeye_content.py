#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from unittest.mock import patch

from cmk.agent_based.v2 import Result, Service
from cmk.plugins.fireeye.agent_based.fireeye_content import (
    check_fireeye_content,
    discover_fireeye_content,
    parse_fireeye_content,
)


def test_fireeye_content_discovery() -> None:
    """Test discovery of FireEye content status."""
    # SNMP data: [version, status, timestamp]
    parsed = parse_fireeye_content([["456.180", "1", "2016/02/26 15:42:06"]])
    assert parsed is not None

    assert list(discover_fireeye_content(parsed)) == [Service()]


def test_fireeye_content_check_ok() -> None:
    """Test FireEye content check with successful update."""
    # SNMP data: [version, status, timestamp] - status "1" means OK
    parsed = parse_fireeye_content([["456.180", "1", "2016/02/26 15:42:06"]])
    assert parsed is not None

    # Freeze time to match expected age calculation
    with patch("time.time", return_value=1468656060.0):  # 2017-07-16T08:21:00
        results = [r for r in check_fireeye_content({}, parsed) if isinstance(r, Result)]

    # Check the structure and key messages
    assert len(results) == 3
    assert results[0].summary == "Last update: 2016/02/26 15:42:06"
    assert "Age:" in results[1].summary
    assert results[2].summary == "Security version: 456.180"
