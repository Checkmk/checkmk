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

from cmk.base.legacy_checks.hp_proliant import check_proliant_general, discover_proliant_general


def test_hp_proliant_discovery():
    """Test discovery of HP ProLiant system status."""
    # Pattern 5c: SNMP sensor data (HP server status information)
    string_table = [["2", "2.60 May 23 2018", "CXX43801XX"]]

    # Test discovery
    discovery = list(discover_proliant_general(string_table))
    assert len(discovery) == 1
    assert discovery[0] == (None, {})


def test_hp_proliant_check():
    """Test HP ProLiant system status check."""
    # Pattern 5c: SNMP sensor data
    string_table = [["2", "2.60 May 23 2018", "CXX43801XX"]]

    results = list(check_proliant_general(None, {}, string_table))

    # Should report system status, firmware, and serial number
    assert len(results) == 2  # Returns (state, message) instead of tuple
    assert results[0] == 0  # OK state
    assert "Status: OK" in results[1]
    assert "Firmware: 2.60 May 23 2018" in results[1]
    assert "S/N: CXX43801XX" in results[1]
