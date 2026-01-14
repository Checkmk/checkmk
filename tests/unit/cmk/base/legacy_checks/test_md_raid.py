#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.md import (
    check_md,
    discover_md,
    parse_md,
)


def parsed() -> Mapping[str, Any]:
    """Return parsed data from actual parse function."""
    return parse_md(
        [
            ["Personalities", ":", "[raid1]", "[raid6]", "[raid5]", "[raid4]"],
            ["md1", ":", "active", "raid1", "sdb2[0]", "sdd2[1]"],
            ["182751552", "blocks", "super", "1.2", "[2/2]", "[UU]"],
            ["bitmap:", "1/2", "pages", "[4KB],", "65536KB", "chunk"],
            ["md2", ":", "active", "raid5", "sdf1[5]", "sde1[2]", "sdc1[1]", "sdg1[3]", "sda1[0]"],
            [
                "31255568384",
                "blocks",
                "super",
                "1.2",
                "level",
                "5,",
                "512k",
                "chunk,",
                "algorithm",
                "2",
                "[5/5]",
                "[UUUUU]",
            ],
            [
                "[===============>.....]",
                "check",
                "=",
                "76.0%",
                "(5938607824/7813892096)",
                "finish=255.8min",
                "speed=122145K/sec",
            ],
            ["bitmap:", "0/59", "pages", "[0KB],", "65536KB", "chunk"],
            ["md3", ":", "active", "raid1", "sdd1[1]", "sdb1[0]"],
            ["67107840", "blocks", "super", "1.2", "[2/2]", "[UU]"],
            ["bitmap:", "1/1", "pages", "[4KB],", "65536KB", "chunk"],
        ]
    )


def parsed_with_failed_disks() -> Mapping[str, Any]:
    """Return parsed data with failed disks."""
    return parse_md(
        [
            ["Personalities", ":", "[raid1]"],
            ["md0", ":", "active", "raid1", "sdc3[3]", "sda3[2](F)", "sdb3[1]"],
            ["48837528", "blocks", "super", "1.0", "[2/2]", "[UU]"],
        ]
    )


def test_md_raid_discovery() -> None:
    """Test discovery function."""
    section = parsed()

    discoveries = list(discover_md(section))

    # Should discover RAID devices but exclude RAID0
    assert len(discoveries) >= 3

    # Extract items from discovery tuples
    items = [item for item, params in discoveries]
    assert "md1" in items  # RAID1
    assert "md2" in items  # RAID5
    assert "md3" in items  # RAID1


def test_md_raid_check_active() -> None:
    """Test check function for active RAID."""
    params = None

    results = list(check_md("md1", params, parsed()))

    # Should have multiple results
    assert len(results) >= 2

    # First result should be status - active is OK
    first_result = results[0]
    assert len(first_result) == 2  # state, summary
    state, summary = first_result
    assert state == 0  # OK state
    assert "Status: active" in summary

    # Should have disk information
    disk_result = results[1]
    state, summary = disk_result
    assert state == 0  # OK state
    assert "Spare:" in summary
    assert "Failed:" in summary
    assert "Active:" in summary


def test_md_raid_check_with_check_operation() -> None:
    """Test check function for RAID with ongoing check."""
    params = None

    results = list(check_md("md2", params, parsed()))

    # Should have multiple results including check status
    assert len(results) >= 3

    # Should have check operation status
    check_result = results[-1]
    state, summary = check_result
    assert state == 0  # OK state for check operation
    assert "[Check]" in summary
    assert "76.0%" in summary


def test_md_raid_check_failed_disks() -> None:
    """Test check function with failed disks."""
    params = None
    section = parsed_with_failed_disks()

    results = list(check_md("md0", params, section))

    # Should have results
    assert len(results) >= 2

    # First result - status should be OK even with failed disk if RAID is still active
    first_result = results[0]
    state, summary = first_result
    assert state == 0  # OK state for active RAID
    assert "Status: active" in summary

    # Should show failed disk count
    disk_result = results[1]
    state, summary = disk_result
    assert "Failed: 1" in summary


def test_md_raid_check_missing_item() -> None:
    """Test check function with non-existent item."""
    params = None

    results = list(check_md("md999", params, parsed()))

    # Should return empty results for missing item
    assert len(results) == 0


def test_md_raid_parse_function() -> None:
    """Test that parse function creates expected data structure."""
    section = parsed()

    # Should have MD devices
    assert "md1" in section
    assert "md2" in section
    assert "md3" in section

    # Check md1 structure (RAID1)
    md1 = section["md1"]
    assert md1["raid_name"] == "raid1"
    assert md1["raid_state"] == "active"
    assert md1["spare_disks"] == 0
    assert md1["failed_disks"] == 0
    assert md1["active_disks"] == 2
    assert md1["num_disks"] == 2
    assert md1["expected_disks"] == 2
    assert md1["working_disks"] == "UU"

    # Check md2 structure (RAID5 with check operation)
    md2 = section["md2"]
    assert md2["raid_name"] == "raid5"
    assert md2["raid_state"] == "active"
    assert md2["active_disks"] == 5
    assert "check_values" in md2
    assert md2["finish"] == "255.8min"
    assert md2["speed"] == "122145K/sec"


def test_md_raid_parse_failed_disks() -> None:
    """Test parse function with failed disks."""
    section = parsed_with_failed_disks()

    # Check md0 with failed disk
    md0 = section["md0"]
    assert md0["raid_name"] == "raid1"
    assert md0["failed_disks"] == 1
    assert md0["active_disks"] == 2  # sdc3[3] and sdb3[1]
    assert md0["spare_disks"] == 0
