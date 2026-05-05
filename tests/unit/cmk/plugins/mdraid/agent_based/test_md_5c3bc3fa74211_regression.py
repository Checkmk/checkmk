#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.mdraid.agent_based.md import check_md, discover_md, parse_md, Section


@pytest.fixture
def parsed() -> Section:
    """Create parsed MD RAID data using actual parse function."""
    string_table = [
        ["Personalities", ":", "[linear]", "[raid0]", "[raid1]"],
        ["md1", ":", "active", "linear", "sda3[0]", "sdb3[1]"],
        ["491026496", "blocks", "64k", "rounding"],
        ["md0", ":", "active", "raid0", "sda2[0]", "sdb2[1]"],
        ["2925532672", "blocks", "64k", "chunks"],
        ["unused", "devices:", "<none>"],
    ]
    return parse_md(string_table)


def test_md_discovery(parsed: Section) -> None:
    """Test MD RAID discovery function."""
    result = list(discover_md(parsed))

    # Should discover md1 (linear) but not md0 (raid0)
    assert result == [Service(item="md1")]


def test_md_check_md1_active_linear(parsed: Section) -> None:
    """Test MD RAID check function for active linear device md1."""
    result = list(check_md("md1", {}, parsed))

    assert result == [
        Result(state=State.OK, summary="Status: active"),
        Result(state=State.OK, summary="Spare: 0, Failed: 0, Active: 2"),
    ]


def test_md_check_md0_raid0_not_discovered(parsed: Section) -> None:
    """Test MD RAID check function for raid0 device md0 that should not be discovered."""
    result = list(check_md("md0", {}, parsed))

    assert result == [
        Result(state=State.OK, summary="Status: active"),
        Result(state=State.OK, summary="Spare: 0, Failed: 0, Active: 2"),
    ]


def test_md_check_missing_item(parsed: Section) -> None:
    """Test MD RAID check function for missing device."""
    result = list(check_md("md99", {}, parsed))

    assert len(result) == 0


def test_md_parse_function() -> None:
    """Test MD RAID parse function with the exact dataset."""
    string_table = [
        ["Personalities", ":", "[linear]", "[raid0]", "[raid1]"],
        ["md1", ":", "active", "linear", "sda3[0]", "sdb3[1]"],
        ["491026496", "blocks", "64k", "rounding"],
        ["md0", ":", "active", "raid0", "sda2[0]", "sdb2[1]"],
        ["2925532672", "blocks", "64k", "chunks"],
        ["unused", "devices:", "<none>"],
    ]

    result = parse_md(string_table)

    assert "md1" in result
    assert "md0" in result

    md1_data = result["md1"]
    assert md1_data["raid_name"] == "linear"
    assert md1_data["raid_state"] == "active"
    assert md1_data["spare_disks"] == 0
    assert md1_data["failed_disks"] == 0
    assert md1_data["active_disks"] == 2

    md0_data = result["md0"]
    assert md0_data["raid_name"] == "raid0"
    assert md0_data["raid_state"] == "active"
    assert md0_data["spare_disks"] == 0
    assert md0_data["failed_disks"] == 0
    assert md0_data["active_disks"] == 2
