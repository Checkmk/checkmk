#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.base.legacy_checks.ucd_mem import check_ucd_mem, discover_ucd_mem
from cmk.plugins.collection.agent_based.ucd_mem import parse_ucd_mem


@pytest.fixture(name="parsed", scope="module")
def fixture_parsed() -> Mapping[str, int]:
    string_table = [
        [
            [
                "64313712",  # MemTotalReal
                "3845212",  # MemAvailReal
                "8388604",  # MemTotalSwap
                "8388604",  # MemAvailSwap
                "12233816",  # MemTotalFree
                "16000",  # memMinimumSwap
                "3163972",  # memShared
                "30364",  # memBuffer
                "10216780",  # memCached
                "1",  # memSwapError (1 = error)
                "foobar",  # memErrorName (different from standard)
                "some error message",  # smemSwapErrorMsg
            ]
        ]
    ]
    return parse_ucd_mem(string_table)


def test_discover_ucd_mem(parsed: Mapping[str, int]) -> None:
    result = list(discover_ucd_mem(parsed))
    assert result == [(None, {})]


def test_check_ucd_mem_with_warning_thresholds(parsed: Mapping[str, int]) -> None:
    """Test with warning/critical thresholds for RAM usage"""
    result = check_ucd_mem(
        None,
        {
            "levels_ram": ("perc_used", (20.0, 30.0)),  # Lower thresholds than actual usage
        },
        parsed,
    )

    result_list = list(result)
    assert len(result_list) == 5  # Including error message

    # Error check first
    state, summary = result_list[0][:2]
    assert state == 1  # WARN
    assert "Error: foobar" in summary

    # RAM usage check - should trigger CRIT since 78% > 30%
    state, summary, metrics = result_list[1]
    assert state == 2  # CRIT
    assert "RAM: 78.09%" in summary
    assert "warn/crit at 20.00%/30.00% used" in summary
    assert len(metrics) == 2
    assert metrics[0][0] == "mem_used"
    assert metrics[1][0] == "mem_used_percent"
    # Check thresholds are properly set
    assert metrics[1][2] == 20.0  # warn threshold
    assert abs(metrics[1][3] - 30.0) < 0.1  # crit threshold (allowing for floating point)

    # Swap usage check
    state, summary, metrics = result_list[2]
    assert state == 0
    assert "Swap: 0%" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "swap_used"

    # Total virtual memory check
    state, summary = result_list[3][:2]
    assert state == 0
    assert "Total virtual memory: 69.08%" in summary

    # Swap error check
    state, summary = result_list[4][:2]
    assert state == 0  # Info level for swap error
    assert "Swap error: some error message" in summary


def test_check_ucd_mem_no_thresholds() -> None:
    """Test without thresholds (should not trigger warnings)"""
    string_table = [
        [
            [
                "64313712",  # MemTotalReal
                "3845212",  # MemAvailReal
                "8388604",  # MemTotalSwap
                "8388604",  # MemAvailSwap
                "12233816",  # MemTotalFree
                "16000",  # memMinimumSwap
                "3163972",  # memShared
                "30364",  # memBuffer
                "10216780",  # memCached
                "0",  # memSwapError (0 = no error)
                "",  # memErrorName
                "",  # smemSwapErrorMsg
            ]
        ]
    ]
    parsed = parse_ucd_mem(string_table)

    result = list(check_ucd_mem(None, {}, parsed))

    # Should have only 3 results (no error message, no swap error)
    assert len(result) == 3

    # All should be OK since no thresholds set
    for item in result:
        if len(item) >= 2 and "Total virtual memory" not in item[1]:  # Skip summary
            assert item[0] == 0  # OK state
