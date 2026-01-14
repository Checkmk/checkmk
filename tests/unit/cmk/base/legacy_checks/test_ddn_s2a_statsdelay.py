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

"""Pattern 5: Standalone test with embedded test data for DDN S2A storage system statistics monitoring."""

from cmk.base.legacy_checks.ddn_s2a_statsdelay import (
    check_ddn_s2a_statsdelay,
    discover_ddn_s2a_statsdelay,
    parse_ddn_s2a_statsdelay,
)

from .checktestlib import mock_item_state


def test_ddn_s2a_statsdelay_discovery():
    """Test discovery of DDN S2A statsdelay services."""
    # Pattern 5d: Storage system monitoring data
    string_table = [
        [
            "0@106@time_interval_in_seconds@0.1@host_reads@696778332@host_writes@171313693@disk_reads@96732186@disk_writes@2717578@time_interval_in_seconds@0.2@host_reads@128302@host_writes@19510@disk_reads@120584@disk_writes@40175@time_interval_in_seconds@0.3@host_reads@10803@host_writes@5428@disk_reads@7028@disk_writes@1645@time_interval_in_seconds@0.4@host_reads@2662@host_writes@2846@disk_reads@1687@disk_writes@270@time_interval_in_seconds@0.5@host_reads@71@host_writes@1588@disk_reads@48@disk_writes@10@time_interval_in_seconds@0.6@host_reads@22@host_writes@925@disk_reads@17@disk_writes@2@time_interval_in_seconds@0.7@host_reads@33@host_writes@611@disk_reads@9@disk_writes@0@time_interval_in_seconds@0.8@host_reads@4@host_writes@331@disk_reads@3@disk_writes@0@time_interval_in_seconds@0.9@host_reads@5@host_writes@249@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.0@host_reads@0@host_writes@116@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.1@host_reads@0@host_writes@52@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.2@host_reads@0@host_writes@19@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.3@host_reads@0@host_writes@20@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.4@host_reads@0@host_writes@14@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.5@host_reads@0@host_writes@11@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.6@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.7@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.8@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.9@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@2.0@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@additional_intervals@1@time_interval_in_seconds@>10.0@host_reads@0@host_writes@3@disk_reads@0@disk_writes@0@$"
        ],
        ["OVER"],
    ]

    parsed = parse_ddn_s2a_statsdelay(string_table)
    result = list(discover_ddn_s2a_statsdelay(parsed))

    # Should discover both Disk and Host services
    assert len(result) == 2
    assert ("Disk", {}) in result
    assert ("Host", {}) in result


def test_ddn_s2a_statsdelay_check_disk():
    """Test DDN S2A statsdelay check for Disk service."""
    # Pattern 5d: Storage system monitoring data
    string_table = [
        [
            "0@106@time_interval_in_seconds@0.1@host_reads@696778332@host_writes@171313693@disk_reads@96732186@disk_writes@2717578@time_interval_in_seconds@0.2@host_reads@128302@host_writes@19510@disk_reads@120584@disk_writes@40175@time_interval_in_seconds@0.3@host_reads@10803@host_writes@5428@disk_reads@7028@disk_writes@1645@time_interval_in_seconds@0.4@host_reads@2662@host_writes@2846@disk_reads@1687@disk_writes@270@time_interval_in_seconds@0.5@host_reads@71@host_writes@1588@disk_reads@48@disk_writes@10@time_interval_in_seconds@0.6@host_reads@22@host_writes@925@disk_reads@17@disk_writes@2@time_interval_in_seconds@0.7@host_reads@33@host_writes@611@disk_reads@9@disk_writes@0@time_interval_in_seconds@0.8@host_reads@4@host_writes@331@disk_reads@3@disk_writes@0@time_interval_in_seconds@0.9@host_reads@5@host_writes@249@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.0@host_reads@0@host_writes@116@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.1@host_reads@0@host_writes@52@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.2@host_reads@0@host_writes@19@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.3@host_reads@0@host_writes@20@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.4@host_reads@0@host_writes@14@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.5@host_reads@0@host_writes@11@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.6@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.7@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.8@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.9@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@2.0@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@additional_intervals@1@time_interval_in_seconds@>10.0@host_reads@0@host_writes@3@disk_reads@0@disk_writes@0@$"
        ],
        ["OVER"],
    ]

    parsed = parse_ddn_s2a_statsdelay(string_table)
    params = {"read_avg": (0.1, 0.2), "write_avg": (0.1, 0.2)}

    # Mock item state with previous histogram data for comparison
    mock_state = {
        "time_intervals": [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            30,
        ],
        "reads": [86732186, 110584, 6028, 687, 45, 13, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "writes": [2617578, 39175, 645, 230, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    }

    with mock_item_state(mock_state):
        results = list(check_ddn_s2a_statsdelay("Disk", params, parsed))

    # Should return 6 results: avg/min/max for both read and write
    assert len(results) == 6
    # Check that we get warning states for average delays
    assert any(result[0] == 1 for result in results)  # Warning state
    assert any("Average read wait" in result[1] for result in results)
    assert any("Average write wait" in result[1] for result in results)


def test_ddn_s2a_statsdelay_check_host():
    """Test DDN S2A statsdelay check for Host service."""
    # Pattern 5d: Storage system monitoring data
    string_table = [
        [
            "0@106@time_interval_in_seconds@0.1@host_reads@696778332@host_writes@171313693@disk_reads@96732186@disk_writes@2717578@time_interval_in_seconds@0.2@host_reads@128302@host_writes@19510@disk_reads@120584@disk_writes@40175@time_interval_in_seconds@0.3@host_reads@10803@host_writes@5428@disk_reads@7028@disk_writes@1645@time_interval_in_seconds@0.4@host_reads@2662@host_writes@2846@disk_reads@1687@disk_writes@270@time_interval_in_seconds@0.5@host_reads@71@host_writes@1588@disk_reads@48@disk_writes@10@time_interval_in_seconds@0.6@host_reads@22@host_writes@925@disk_reads@17@disk_writes@2@time_interval_in_seconds@0.7@host_reads@33@host_writes@611@disk_reads@9@disk_writes@0@time_interval_in_seconds@0.8@host_reads@4@host_writes@331@disk_reads@3@disk_writes@0@time_interval_in_seconds@0.9@host_reads@5@host_writes@249@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.0@host_reads@0@host_writes@116@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.1@host_reads@0@host_writes@52@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.2@host_reads@0@host_writes@19@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.3@host_reads@0@host_writes@20@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.4@host_reads@0@host_writes@14@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.5@host_reads@0@host_writes@11@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.6@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.7@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.8@host_reads@0@host_writes@1@disk_reads@0@disk_writes@0@time_interval_in_seconds@1.9@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@time_interval_in_seconds@2.0@host_reads@0@host_writes@0@disk_reads@0@disk_writes@0@additional_intervals@1@time_interval_in_seconds@>10.0@host_reads@0@host_writes@3@disk_reads@0@disk_writes@0@$"
        ],
        ["OVER"],
    ]

    parsed = parse_ddn_s2a_statsdelay(string_table)
    params = {"read_avg": (0.1, 0.2), "write_avg": (0.1, 0.2)}

    # Mock item state with previous histogram data
    mock_state = {
        "time_intervals": [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            30,
        ],
        "reads": [
            696650030,
            128202,
            10703,
            2592,
            66,
            17,
            28,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ],
        "writes": [
            171293183,
            19458,
            5408,
            2836,
            1578,
            923,
            611,
            331,
            248,
            113,
            49,
            16,
            17,
            11,
            8,
            0,
            0,
            0,
            0,
            0,
            0,
        ],
    }

    with mock_item_state(mock_state):
        results = list(check_ddn_s2a_statsdelay("Host", params, parsed))

    # Should return 6 results: avg/min/max for both read and write
    assert len(results) == 6
    # Check that we get warning states for average delays
    assert any(result[0] == 1 for result in results)  # Warning state
    assert any("Average read wait" in result[1] for result in results)
    assert any("Average write wait" in result[1] for result in results)
