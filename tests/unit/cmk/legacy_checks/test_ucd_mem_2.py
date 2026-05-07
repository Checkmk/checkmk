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
from cmk.legacy_checks.ucd_mem import check_ucd_mem, discover_ucd_mem
from cmk.plugins.ucd.agent_based.ucd_mem import parse_ucd_mem, Section


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
            "swap",  # memErrorName
            "some error message",  # smemSwapErrorMsg
        ]
    ]
    assert (section := parse_ucd_mem(string_table))
    return section


def test_discover_ucd_mem(parsed: Section) -> None:
    assert list(discover_ucd_mem(parsed)) == [Service()]


def test_check_ucd_mem_with_swap_error(parsed: Section) -> None:
    result = list(
        check_ucd_mem(
            {
                "levels_ram": ("perc_used", (80.0, 90.0)),
                "swap_errors": 2,
            },
            parsed,
        )
    )

    text_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]

    # RAM usage check
    assert text_results[0].state == State.OK
    assert "RAM: 78.09%" in text_results[0].summary
    assert "47.9 GiB of 61.3 GiB" in text_results[0].summary

    # Swap usage check
    assert text_results[1].state == State.OK
    assert "Swap: 0%" in text_results[1].summary
    assert "0 B of 8.00 GiB" in text_results[1].summary

    # Total virtual memory check
    assert text_results[2].state == State.OK
    assert "Total virtual memory: 69.08%" in text_results[2].summary
    assert "47.9 GiB of 69.3 GiB" in text_results[2].summary

    # Swap error check
    assert text_results[3].state == State.CRIT
    assert "Swap error: some error message" in text_results[3].summary

    metric_names = {m.name for m in metrics}
    assert {"mem_used", "mem_used_percent", "swap_used"} <= metric_names


def test_check_ucd_mem_no_swap_error() -> None:
    """Test without swap error condition"""
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

    result = list(check_ucd_mem({"levels_ram": ("perc_used", (80.0, 90.0))}, section))
    text_results = [r for r in result if isinstance(r, Result)]
    # Check that no swap error is reported
    for r in text_results:
        assert "Swap error" not in r.summary
