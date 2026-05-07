#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.ucd_mem import check_ucd_mem, discover_ucd_mem
from cmk.plugins.ucd.agent_based.ucd_mem import parse_ucd_mem, Section


def parsed() -> Section:
    """Parsed UCD memory data for testing."""
    string_table = [
        [
            "64313712",
            "3845212",
            "8388604",
            "8388604",
            "12233816",
            "16000",
            "3163972",
            "30364",
            "10216780",
            "0",
            "swap",
            "",
        ]
    ]
    assert (section := parse_ucd_mem(string_table))
    return section


def test_ucd_mem_1_discovery() -> None:
    """Test ucd_mem discovery."""
    assert list(discover_ucd_mem(parsed())) == [Service()]


def test_ucd_mem_1_check() -> None:
    """Test ucd_mem check."""
    params = {"levels_ram": ("perc_used", (80.0, 90.0))}
    result = list(check_ucd_mem(params, parsed()))

    text_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]

    # Check RAM result
    assert text_results[0].state == State.OK
    assert "RAM:" in text_results[0].summary
    assert "78.09%" in text_results[0].summary
    assert "47.9 GiB of 61.3 GiB" in text_results[0].summary

    # Check Swap result
    assert "Swap:" in text_results[1].summary
    assert text_results[1].state == State.OK
    assert "0% - 0 B of 8.00 GiB" in text_results[1].summary

    # Check Total virtual memory result
    assert text_results[2].state == State.OK
    assert "Total virtual memory:" in text_results[2].summary
    assert "69.08%" in text_results[2].summary
    assert "47.9 GiB of 69.3 GiB" in text_results[2].summary

    metric_names = {m.name for m in metrics}
    assert {"mem_used", "mem_used_percent", "swap_used"} <= metric_names
