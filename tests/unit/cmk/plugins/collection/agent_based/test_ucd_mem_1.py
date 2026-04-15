#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.ucd_mem import (
    check_ucd_mem,
    discover_ucd_mem,
    parse_ucd_mem,
)


def parsed() -> Mapping[str, Any]:
    """Parsed UCD memory data for testing."""
    string_table = [
        [
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
    ]
    return parse_ucd_mem(string_table)


def test_ucd_mem_1_discovery() -> None:
    """Test ucd_mem discovery."""
    services = list(discover_ucd_mem(parsed()))
    assert services == [Service()]


def test_ucd_mem_1_check() -> None:
    """Test ucd_mem check."""
    params: dict[str, Any] = {"levels_ram": (80.0, 90.0)}
    results = list(check_ucd_mem(params, parsed()))

    # Should have results for RAM, Swap, and Total virtual memory
    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]

    # RAM check
    ram_results = [r for r in result_objs if "RAM:" in r.summary]
    assert len(ram_results) == 1
    assert ram_results[0].state == State.OK
    assert "78.09%" in ram_results[0].summary

    # Swap check
    swap_results = [r for r in result_objs if "Swap:" in r.summary]
    assert len(swap_results) == 1
    assert swap_results[0].state == State.OK

    # Total virtual memory check
    virtual_results = [r for r in result_objs if "Total virtual memory:" in r.summary]
    assert len(virtual_results) == 1
    assert "69.08%" in virtual_results[0].summary

    # Should have metrics for mem_used and swap_used
    metric_names = [m.name for m in metric_objs]
    assert "mem_used" in metric_names
    assert "swap_used" in metric_names
