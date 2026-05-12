#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.network.agent_based.ucd_mem import (
    check_ucd_mem,
    discover_ucd_mem,
    parse_ucd_mem,
    Section,
)


@pytest.fixture(name="parsed", scope="module")
def fixture_parsed() -> Section:
    string_table = [
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
    assert (section := parse_ucd_mem(string_table))
    return section


def test_discover_ucd_mem(parsed: Section) -> None:
    assert list(discover_ucd_mem(parsed)) == [Service()]


def test_check_ucd_mem_with_warning_thresholds(parsed: Section) -> None:
    """Test with warning/critical thresholds for RAM usage"""
    result = list(
        check_ucd_mem(
            {
                "levels_ram": ("perc_used", (20.0, 30.0)),  # Lower thresholds than actual usage
            },
            parsed,
        )
    )

    text_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]

    # Error message first
    assert text_results[0].state == State.WARN
    assert "Error: foobar" in text_results[0].summary

    # RAM usage check - should trigger CRIT since 78% > 30%
    assert text_results[1].state == State.CRIT
    assert "RAM: 78.09%" in text_results[1].summary
    assert "warn/crit at 20.00%/30.00% used" in text_results[1].summary

    # Verify mem_used_percent metric thresholds
    mem_used_percent = next(m for m in metrics if m.name == "mem_used_percent")
    warn_val, crit_val = mem_used_percent.levels
    assert warn_val == 20.0
    assert crit_val is not None
    assert abs(crit_val - 30.0) < 0.1

    # Swap usage check
    assert text_results[2].state == State.OK
    assert "Swap: 0%" in text_results[2].summary

    # Total virtual memory check
    assert text_results[3].state == State.OK
    assert "Total virtual memory: 69.08%" in text_results[3].summary

    # Swap error message - default state 0 since no swap_errors param given (defaults to 0)
    assert text_results[4].state == State.OK
    assert "Swap error: some error message" in text_results[4].summary


def test_check_ucd_mem_no_thresholds() -> None:
    """Test without thresholds (should not trigger warnings)"""
    string_table = [
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
    assert (section := parse_ucd_mem(string_table))

    result = list(check_ucd_mem({}, section))
    text_results = [r for r in result if isinstance(r, Result)]

    # All should be OK since no thresholds set
    for r in text_results:
        assert r.state == State.OK
