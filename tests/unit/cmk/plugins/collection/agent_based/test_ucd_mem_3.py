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

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.ucd_mem import (
    check_ucd_mem,
    discover_ucd_mem,
    parse_ucd_mem,
)


@pytest.fixture(name="parsed", scope="module")
def fixture_parsed() -> Mapping[str, Any]:
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
                "1",
                "foobar",
                "some error message",
            ]
        ]
    ]
    return parse_ucd_mem(string_table)


def test_discover_ucd_mem(parsed: Mapping[str, Any]) -> None:
    result = list(discover_ucd_mem(parsed))
    assert result == [Service()]


def test_check_ucd_mem_with_warning_thresholds(parsed: Mapping[str, Any]) -> None:
    """Test with warning/critical thresholds for RAM usage"""
    results = list(
        check_ucd_mem(
            {
                "levels_ram": ("perc_used", (20.0, 30.0)),
            },
            parsed,
        )
    )

    result_objs = [r for r in results if isinstance(r, Result)]
    metric_objs = [r for r in results if isinstance(r, Metric)]

    # Error check first (foobar != "swap", so yields warning)
    error_results = [r for r in result_objs if "Error: foobar" in r.summary]
    assert len(error_results) == 1
    assert error_results[0].state == State.WARN

    # RAM usage check - should trigger CRIT since 78% > 30%
    ram_results = [r for r in result_objs if "RAM:" in r.summary]
    assert len(ram_results) == 1
    assert ram_results[0].state == State.CRIT
    assert "78.09%" in ram_results[0].summary

    # Should have mem_used metric
    assert any(m.name == "mem_used" for m in metric_objs)

    # Swap error check
    swap_error_results = [r for r in result_objs if "Swap error:" in r.summary]
    assert len(swap_error_results) == 1
    assert "some error message" in swap_error_results[0].summary


def test_check_ucd_mem_no_thresholds() -> None:
    """Test without thresholds (should not trigger warnings)"""
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
                "",
                "",
            ]
        ]
    ]
    parsed = parse_ucd_mem(string_table)

    results = list(check_ucd_mem({}, parsed))
    result_objs = [r for r in results if isinstance(r, Result)]

    # All should be OK since no thresholds set
    for r in result_objs:
        assert r.state == State.OK
