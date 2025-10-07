#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.silverpeak_VX6000 import (
    check_silverpeak,
    discover_silverpeak_VX6000,
    parse_silverpeak,
)


def parsed() -> Mapping[str, Any]:
    """Return parsed data from actual parse function."""
    return parse_silverpeak(
        [
            [["4"]],
            [
                ["0", "Tunnel state is Up", "if1"],
                ["2", "System BYPASS mode", "mysystem"],
                ["4", "Tunnel state is Down", "to_sp01-dnd_WAN-WAN"],
                ["8", "Disk is not in service", "mydisk"],
            ],
        ]
    )


def test_silverpeak_VX6000_discovery() -> None:
    """Test discovery function."""
    section = parsed()

    discoveries = list(discover_silverpeak_VX6000(section))

    # Should discover single alarm service
    assert len(discoveries) == 1

    # Extract item and params from discovery tuple
    item, params = discoveries[0]
    assert item is None  # silverpeak uses None as item
    assert params == {}


def test_silverpeak_VX6000_check_alarms() -> None:
    """Test check function with multiple alarm severities."""
    results = list(check_silverpeak(None, {}, parsed()))

    # Should have 5 results: summary + 4 individual alarms
    assert len(results) == 5

    # Check summary result (first one)
    first_result = results[0]
    assert len(first_result) == 2  # state, summary
    state, summary = first_result
    assert state == 0  # OK state for summary
    assert "4 active alarms" in summary
    assert "OK: 1, WARN: 1, CRIT: 1, UNKNOWN: 1" in summary

    # Check individual alarm results
    alarm_results = results[1:]

    # Extract states from alarm results
    alarm_states = [result[0] for result in alarm_results]

    # Should have one of each state: OK(0), WARN(1), CRIT(2), UNKNOWN(3)
    assert 0 in alarm_states  # info alarm (tunnel up)
    assert 1 in alarm_states  # minor alarm (system bypass)
    assert 2 in alarm_states  # critical alarm (tunnel down)
    assert 3 in alarm_states  # indeterminate alarm (disk not in service)


def test_silverpeak_VX6000_check_no_alarms() -> None:
    """Test check function with no active alarms."""
    # Create section with zero alarm count
    no_alarms_section = parse_silverpeak(
        [
            [["0"]],
            [],
        ]
    )

    results = list(check_silverpeak(None, {}, no_alarms_section))

    # Should have single result indicating no alarms
    assert len(results) == 1

    state, summary = results[0]
    assert state == 0  # OK state
    assert "No active alarms" in summary


def test_silverpeak_VX6000_parse_function() -> None:
    """Test that parse function creates expected data structure."""
    section = parsed()

    # Should have alarm count
    assert "alarm_count" in section
    assert section["alarm_count"] == 4

    # Should have alarms list
    assert "alarms" in section
    alarms = section["alarms"]
    assert len(alarms) == 4

    # Check first alarm (info severity)
    info_alarm = alarms[0]
    assert info_alarm["state"] == 0
    assert info_alarm["severity_as_text"] == "info"
    assert info_alarm["descr"] == "Tunnel state is Up"
    assert info_alarm["source"] == "if1"

    # Check critical alarm
    crit_alarm = alarms[2]
    assert crit_alarm["state"] == 2
    assert crit_alarm["severity_as_text"] == "critical"
    assert crit_alarm["descr"] == "Tunnel state is Down"
    assert crit_alarm["source"] == "to_sp01-dnd_WAN-WAN"


def test_silverpeak_VX6000_discovery_empty_section() -> None:
    """Test discovery with empty section."""
    empty_section: dict[str, Any] = {}

    discoveries = list(discover_silverpeak_VX6000(empty_section))

    # Should not discover anything for empty section
    assert len(discoveries) == 0
