#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.mdraid.agent_based.md import (
    check_md,
    discover_md,
    parse_md,
    Section,
)


def parsed() -> Section:
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


def parsed_with_failed_disks() -> Section:
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

    items = [service.item for service in discoveries]
    assert "md1" in items  # RAID1
    assert "md2" in items  # RAID5
    assert "md3" in items  # RAID1


def test_md_raid_check_active() -> None:
    """Test check function for active RAID."""
    results = list(check_md("md1", {}, parsed()))

    assert len(results) >= 2

    first_result = results[0]
    assert isinstance(first_result, Result)
    assert first_result.state is State.OK
    assert "Status: active" in first_result.summary

    disk_result = results[1]
    assert isinstance(disk_result, Result)
    assert disk_result.state is State.OK
    assert "Spare:" in disk_result.summary
    assert "Failed:" in disk_result.summary
    assert "Active:" in disk_result.summary


def test_md_raid_check_with_check_operation() -> None:
    """Test check function for RAID with ongoing check."""
    results = list(check_md("md2", {}, parsed()))

    assert len(results) >= 3

    check_result = results[-1]
    assert isinstance(check_result, Result)
    assert check_result.state is State.OK
    assert "[Check]" in check_result.summary
    assert "76.0%" in check_result.summary


def test_md_raid_check_failed_disks() -> None:
    """Test check function with failed disks."""
    section = parsed_with_failed_disks()

    results = list(check_md("md0", {}, section))

    assert len(results) >= 2

    first_result = results[0]
    assert isinstance(first_result, Result)
    assert first_result.state is State.OK
    assert "Status: active" in first_result.summary

    disk_result = results[1]
    assert isinstance(disk_result, Result)
    assert "Failed: 1" in disk_result.summary


def test_md_raid_check_missing_item() -> None:
    """Test check function with non-existent item."""
    results = list(check_md("md999", {}, parsed()))

    assert len(results) == 0


def test_md_raid_parse_function() -> None:
    """Test that parse function creates expected data structure."""
    section = parsed()

    assert "md1" in section
    assert "md2" in section
    assert "md3" in section

    md1 = section["md1"]
    assert md1["raid_name"] == "raid1"
    assert md1["raid_state"] == "active"
    assert md1["spare_disks"] == 0
    assert md1["failed_disks"] == 0
    assert md1["active_disks"] == 2
    assert md1["num_disks"] == 2
    assert md1["expected_disks"] == 2
    assert md1["working_disks"] == "UU"

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

    md0 = section["md0"]
    assert md0["raid_name"] == "raid1"
    assert md0["failed_disks"] == 1
    assert md0["active_disks"] == 2
    assert md0["spare_disks"] == 0
