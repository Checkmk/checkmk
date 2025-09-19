#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Pattern 3: UCS rack server fault instance monitoring with special agent data."""

from cmk.base.legacy_checks.ucs_c_rack_server_faultinst import (
    check_ucs_c_rack_server_faultinst,
    discover_ucs_c_rack_server_faultinst,
)
from cmk.plugins.collection.agent_based.ucs_c_rack_server_faultinst import (
    parse_ucs_c_rack_server_faultinst,
)


def test_ucs_c_rack_server_faultinst_discovery():
    """Test discovery of UCS rack server fault instances."""
    # Pattern 3: Empty special agent data (no faults)
    string_table: list[list[str]] = []

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(discover_ucs_c_rack_server_faultinst(parsed))

    # Should always discover one service with None item
    assert len(result) == 1
    assert result[0] == (None, {})


def test_ucs_c_rack_server_faultinst_no_faults():
    """Test check with no fault instances found."""
    # Pattern 3: Empty special agent data
    string_table: list[list[str]] = []

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(check_ucs_c_rack_server_faultinst(None, {}, parsed))

    # Should return OK state with no faults message
    assert len(result) == 1
    assert result[0] == (0, "No fault instances found")


def test_ucs_c_rack_server_faultinst_critical_fault():
    """Test check with critical fault instance."""
    # Pattern 3: Special agent data with critical fault
    string_table = [
        [
            "faultInst",
            "severity critical",
            "cause powerproblem",
            "code F0883",
            "descr Power supply 4 is in a degraded state",
            "affectedDN sys/rack-unit-1/psu-4",
        ]
    ]

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(check_ucs_c_rack_server_faultinst(None, {}, parsed))

    # Should return critical state with fault summary and details
    assert len(result) == 2
    assert result[0][0] == 2  # Critical state
    assert "Found faults: 1 with severity 'critical'" in result[0][1]
    assert result[1][0] == 2  # Individual fault
    assert "Severity: critical" in result[1][1]
    assert "Power supply 4 is in a degraded state" in result[1][1]


def test_ucs_c_rack_server_faultinst_major_fault():
    """Test check with major fault instance."""
    # Pattern 3: Special agent data with major fault
    string_table = [
        [
            "faultInst",
            "severity major",
            "cause equipmentDegraded",
            "code F0969",
            "descr Storage Raid Battery 11 Degraded",
            "affectedDN sys/rack-unit-1/board/storage-SAS-SLOT-SAS/raid-battery-11",
        ]
    ]

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(check_ucs_c_rack_server_faultinst(None, {}, parsed))

    # Should return warning state for major fault
    assert len(result) == 2
    assert result[0][0] == 1  # Warning state
    assert "Found faults: 1 with severity 'major'" in result[0][1]
    assert result[1][0] == 1  # Individual fault warning
    assert "Storage Raid Battery 11 Degraded" in result[1][1]


def test_ucs_c_rack_server_faultinst_info_fault():
    """Test check with info level fault instance."""
    # Pattern 3: Special agent data with info fault
    string_table = [
        [
            "faultInst",
            "severity info",
            "cause configuration",
            "code F1234",
            "descr Configuration change detected",
            "affectedDN sys/rack-unit-1/config",
        ]
    ]

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(check_ucs_c_rack_server_faultinst(None, {}, parsed))

    # Should return OK state for info fault
    assert len(result) == 2
    assert result[0][0] == 0  # OK state
    assert "Found faults: 1 with severity 'info'" in result[0][1]
    assert result[1][0] == 0  # Individual fault OK
    assert "Configuration change detected" in result[1][1]


def test_ucs_c_rack_server_faultinst_multiple_faults():
    """Test check with multiple fault instances of different severities."""
    # Pattern 3: Special agent data with multiple faults
    string_table = [
        [
            "faultInst",
            "severity critical",
            "cause powerproblem",
            "code F0883",
            "descr Power supply 4 is in a degraded state",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity major",
            "cause psuRedundancyFail",
            "code F0743",
            "descr Power Supply redundancy is lost",
            "affectedDN sys/rack-unit-1/psu",
        ],
        [
            "faultInst",
            "severity info",
            "cause configuration",
            "code F1234",
            "descr Configuration change detected",
            "affectedDN sys/rack-unit-1/config",
        ],
    ]

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(check_ucs_c_rack_server_faultinst(None, {}, parsed))

    # Should return critical state (highest severity)
    assert len(result) == 4  # Summary + 3 individual faults
    assert result[0][0] == 2  # Critical overall state
    assert "Found faults:" in result[0][1]
    assert "critical" in result[0][1] and "major" in result[0][1] and "info" in result[0][1]

    # Individual faults are sorted by state (severity mapping)
    # The order depends on the sorting algorithm in the legacy check
    states = [result[i][0] for i in range(1, 4)]
    assert 2 in states  # Critical fault present
    assert 1 in states  # Major fault present
    assert 0 in states  # Info fault present


def test_ucs_c_rack_server_faultinst_unknown_severity():
    """Test check with unknown severity fault instance."""
    # Pattern 3: Special agent data with unknown severity
    string_table = [
        [
            "faultInst",
            "severity unknown",
            "cause unknown",
            "code F9999",
            "descr Unknown fault condition",
            "affectedDN sys/rack-unit-1/unknown",
        ]
    ]

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(check_ucs_c_rack_server_faultinst(None, {}, parsed))

    # Should return unknown state (3) for unmapped severity
    assert len(result) == 2
    assert result[0][0] == 3  # Unknown state
    assert "Found faults: 1 with severity 'unknown'" in result[0][1]
    assert result[1][0] == 3  # Individual fault unknown
    assert "Unknown fault condition" in result[1][1]
