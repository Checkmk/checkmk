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

"""Pattern 3: UCS rack server fault instance monitoring with special agent data."""

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.base.legacy_checks.ucs_c_rack_server_faultinst import (
    check_ucs_c_rack_server_faultinst,
    discover_ucs_c_rack_server_faultinst,
    parse_ucs_c_rack_server_faultinst,
)


@pytest.fixture(name="string_table")
def fixture_string_table() -> list[list[str]]:
    """UCS rack server fault instance data with different severity levels.

    Tests all possible severity states and their mapping to monitoring states:
    - info, condition, cleared -> OK (0)
    - minor, warning, major -> WARNING (1)
    - critical -> CRITICAL (2)
    - unknown -> UNKNOWN (3)
    """
    return [
        [
            "faultInst",
            "severity info",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity condition",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity cleared",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity minor",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity warning",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity major",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity critical",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity unknown",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
    ]


@pytest.fixture(name="parsed_data")
def fixture_parsed_data(string_table: list[list[str]]) -> Mapping[str, Sequence[str]]:
    """Parsed UCS fault instance data."""
    return parse_ucs_c_rack_server_faultinst(string_table)


def test_parse_ucs_c_rack_server_faultinst_multiple_severities(
    string_table: list[list[str]],
) -> None:
    """Test parsing UCS fault instances with multiple severity levels."""
    parsed = parse_ucs_c_rack_server_faultinst(string_table)

    assert len(parsed["Severity"]) == 8
    expected_severities = [
        "info",
        "condition",
        "cleared",
        "minor",
        "warning",
        "major",
        "critical",
        "unknown",
    ]
    assert parsed["Severity"] == expected_severities

    # All should have same cause, code, description
    assert all(cause == "powerproblem" for cause in parsed["Cause"])
    assert all(code == "F0883" for code in parsed["Code"])
    assert all(desc == "Broken" for desc in parsed["Description"])

    # Affected DN should have sys/ prefix removed
    assert all(dn == "rack-unit-1/psu-4" for dn in parsed["Affected DN"])


def test_parse_ucs_c_rack_server_faultinst_empty_data() -> None:
    """Test parsing with empty data."""
    parsed = parse_ucs_c_rack_server_faultinst([])
    assert parsed == {}


def test_parse_ucs_c_rack_server_faultinst_single_fault() -> None:
    """Test parsing with single fault instance."""
    string_table = [
        [
            "faultInst",
            "severity critical",
            "cause powerproblem",
            "code F0883",
            "descr Power supply failure",
            "affectedDN sys/rack-unit-1/psu-2",
        ]
    ]

    parsed = parse_ucs_c_rack_server_faultinst(string_table)

    assert parsed["Severity"] == ["critical"]
    assert parsed["Cause"] == ["powerproblem"]
    assert parsed["Code"] == ["F0883"]
    assert parsed["Description"] == ["Power supply failure"]
    assert parsed["Affected DN"] == ["rack-unit-1/psu-2"]


def test_discover_ucs_c_rack_server_faultinst(parsed_data: dict[str, list[str]]) -> None:
    """Test discovery of UCS fault instance service."""
    items = list(discover_ucs_c_rack_server_faultinst(parsed_data))

    assert len(items) == 1
    assert items[0] == Service()


def test_discover_ucs_c_rack_server_faultinst_empty_data() -> None:
    """Test discovery with empty data."""
    items = list(discover_ucs_c_rack_server_faultinst({}))

    assert len(items) == 1
    assert items[0] == Service()


def test_check_ucs_c_rack_server_faultinst_multiple_severities(
    parsed_data: dict[str, list[str]],
) -> None:
    """Test check function with multiple fault severities."""
    results = list(check_ucs_c_rack_server_faultinst(parsed_data))
    assert results == [
        Result(
            state=State.CRIT,
            summary="Found faults: 1 with severity 'cleared', 1 with severity 'condition', 1 with severity 'critical', 1 with severity 'info', 1 with severity 'major', 1 with severity 'minor', 1 with severity 'unknown', 1 with severity 'warning'",
        ),
        Result(
            state=State.OK,
            notice="Individual faults: Severity: info, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
        Result(
            state=State.OK,
            notice="Severity: condition, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
        Result(
            state=State.OK,
            notice="Severity: cleared, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
        Result(
            state=State.WARN,
            summary="Severity: minor, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
        Result(
            state=State.WARN,
            summary="Severity: warning, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
        Result(
            state=State.WARN,
            summary="Severity: major, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
        Result(
            state=State.CRIT,
            summary="Severity: critical, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
        Result(
            state=State.UNKNOWN,
            summary="Severity: unknown, Description: Broken, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
    ]


def test_check_ucs_c_rack_server_faultinst_empty_data() -> None:
    """Test check function with no fault instances."""
    results = list(check_ucs_c_rack_server_faultinst({}))
    assert results == [
        Result(state=State.OK, summary="No fault instances found"),
    ]


def test_check_ucs_c_rack_server_faultinst_only_warnings() -> None:
    """Test check function with only warning-level faults."""
    parsed_data = {
        "Severity": ["minor", "warning"],
        "Cause": ["powerproblem", "powerproblem"],
        "Code": ["F0883", "F0883"],
        "Description": ["Issue 1", "Issue 2"],
        "Affected DN": ["rack-unit-1/psu-1", "rack-unit-1/psu-2"],
    }

    results = list(check_ucs_c_rack_server_faultinst(parsed_data))
    assert results == [
        Result(
            state=State.WARN,
            summary="Found faults: 1 with severity 'minor', 1 with severity 'warning'",
        ),
        Result(
            state=State.WARN,
            summary="Individual faults: Severity: minor, Description: Issue 1, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-1",
        ),
        Result(
            state=State.WARN,
            summary="Severity: warning, Description: Issue 2, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-2",
        ),
    ]


def test_check_ucs_c_rack_server_faultinst_critical_present() -> None:
    """Test check function prioritizes critical faults in overall state."""
    parsed_data = {
        "Severity": ["info", "critical", "warning"],
        "Cause": ["cause1", "cause2", "cause3"],
        "Code": ["F001", "F002", "F003"],
        "Description": ["Info fault", "Critical fault", "Warning fault"],
        "Affected DN": ["dn1", "dn2", "dn3"],
    }

    results = list(check_ucs_c_rack_server_faultinst(parsed_data))
    assert results == [
        Result(
            state=State.CRIT,
            summary="Found faults: 1 with severity 'critical', 1 with severity 'info', 1 with severity 'warning'",
        ),
        Result(
            state=State.OK,
            notice="Individual faults: Severity: info, Description: Info fault, Cause: cause1, Code: F001, Affected DN: dn1",
        ),
        Result(
            state=State.WARN,
            summary="Severity: warning, Description: Warning fault, Cause: cause3, Code: F003, Affected DN: dn3",
        ),
        Result(
            state=State.CRIT,
            summary="Severity: critical, Description: Critical fault, Cause: cause2, Code: F002, Affected DN: dn2",
        ),
    ]


def test_ucs_c_rack_server_faultinst_discovery():
    """Test discovery of UCS rack server fault instances."""
    # Pattern 3: Empty special agent data (no faults)
    string_table: list[list[str]] = []

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(discover_ucs_c_rack_server_faultinst(parsed))

    # Should always discover one service with no item
    assert len(result) == 1
    assert result[0] == Service()


def test_ucs_c_rack_server_faultinst_no_faults():
    """Test check with no fault instances found."""
    # Pattern 3: Empty special agent data
    string_table: list[list[str]] = []

    parsed = parse_ucs_c_rack_server_faultinst(string_table)
    result = list(check_ucs_c_rack_server_faultinst(parsed))

    # Should return OK state with no faults message
    assert len(result) == 1
    assert result[0] == Result(state=State.OK, summary="No fault instances found")


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
    result = list(check_ucs_c_rack_server_faultinst(parsed))
    assert result == [
        Result(state=State.CRIT, summary="Found faults: 1 with severity 'critical'"),
        Result(
            state=State.CRIT,
            summary="Individual faults: Severity: critical, Description: Power supply 4 is in a degraded state, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
    ]


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
    result = list(check_ucs_c_rack_server_faultinst(parsed))
    assert result == [
        Result(state=State.WARN, summary="Found faults: 1 with severity 'major'"),
        Result(
            state=State.WARN,
            summary="Individual faults: Severity: major, Description: Storage Raid Battery 11 Degraded, Cause: equipmentDegraded, Code: F0969, Affected DN: rack-unit-1/board/storage-SAS-SLOT-SAS/raid-battery-11",
        ),
    ]


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
    result = list(check_ucs_c_rack_server_faultinst(parsed))
    assert result == [
        Result(state=State.OK, summary="Found faults: 1 with severity 'info'"),
        Result(
            state=State.OK,
            notice="Individual faults: Severity: info, Description: Configuration change detected, Cause: configuration, Code: F1234, Affected DN: rack-unit-1/config",
        ),
    ]


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
    result = list(check_ucs_c_rack_server_faultinst(parsed))
    assert result == [
        Result(
            state=State.CRIT,
            summary="Found faults: 1 with severity 'critical', 1 with severity 'info', 1 with severity 'major'",
        ),
        Result(
            state=State.OK,
            notice="Individual faults: Severity: info, Description: Configuration change detected, Cause: configuration, Code: F1234, Affected DN: rack-unit-1/config",
        ),
        Result(
            state=State.WARN,
            summary="Severity: major, Description: Power Supply redundancy is lost, Cause: psuRedundancyFail, Code: F0743, Affected DN: rack-unit-1/psu",
        ),
        Result(
            state=State.CRIT,
            summary="Severity: critical, Description: Power supply 4 is in a degraded state, Cause: powerproblem, Code: F0883, Affected DN: rack-unit-1/psu-4",
        ),
    ]


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
    result = list(check_ucs_c_rack_server_faultinst(parsed))
    assert result == [
        Result(state=State.UNKNOWN, summary="Found faults: 1 with severity 'unknown'"),
        Result(
            state=State.UNKNOWN,
            summary="Individual faults: Severity: unknown, Description: Unknown fault condition, Cause: unknown, Code: F9999, Affected DN: rack-unit-1/unknown",
        ),
    ]
