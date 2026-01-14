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
                "swap",  # memErrorName
                "some error message",  # smemSwapErrorMsg
            ]
        ]
    ]
    return parse_ucd_mem(string_table)


def test_discover_ucd_mem(parsed: Mapping[str, int]) -> None:
    result = list(discover_ucd_mem(parsed))
    assert result == [(None, {})]


def test_check_ucd_mem_with_swap_error(parsed: Mapping[str, int]) -> None:
    result = check_ucd_mem(
        None,
        {
            "levels_ram": (80.0, 90.0),
            "swap_errors": 2,
        },
        parsed,
    )

    result_list = list(result)
    assert len(result_list) == 4

    # RAM usage check
    state, summary, metrics = result_list[0]
    assert state == 0
    assert "RAM: 78.09%" in summary
    assert "47.9 GiB of 61.3 GiB" in summary
    assert len(metrics) == 2
    assert metrics[0][0] == "mem_used"
    assert metrics[1][0] == "mem_used_percent"

    # Swap usage check
    state, summary, metrics = result_list[1]
    assert state == 0
    assert "Swap: 0%" in summary
    assert "0 B of 8.00 GiB" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "swap_used"

    # Total virtual memory check
    state, summary = result_list[2][:2]
    assert state == 0
    assert "Total virtual memory: 69.08%" in summary
    assert "47.9 GiB of 69.3 GiB" in summary

    # Swap error check
    state, summary = result_list[3][:2]
    assert state == 2
    assert "Swap error: some error message" in summary


def test_check_ucd_mem_no_swap_error() -> None:
    """Test without swap error condition"""
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

    result = list(check_ucd_mem(None, {"levels_ram": (80.0, 90.0)}, parsed))

    # Should have only 3 results (no swap error)
    assert len(result) == 3

    # Check that no swap error is reported
    for item in result:
        assert "Swap error" not in item[1]
