#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest
import time_machine

from cmk.agent_based.v2 import GetRateError
from cmk.base.legacy_checks import kernel
from cmk.plugins.collection.agent_based.kernel import parse_kernel, Section


@pytest.fixture
def parsed() -> Section:
    """Create parsed kernel data using actual parse function."""
    string_table = [
        ["11238"],
        ["nr_free_pages", "198749"],
        ["pgpgin", "169984814"],
        ["pgpgout", "97137765"],
        ["pswpin", "250829"],
        ["pswpout", "751706"],
        ["pgmajfault", "1795031"],
        ["cpu", "13008772", "12250", "5234590", "181918601", "73242", "0", "524563", "0", "0", "0"],
        ["cpu0", "1602366", "1467", "675813", "22730303", "9216", "0", "265437", "0", "0", "0"],
        ["cpu1", "1463624", "1624", "576516", "22975174", "8376", "0", "116908", "0", "0", "0"],
        ["ctxt", "539210403"],
        ["processes", "4700038"],
    ]
    return parse_kernel(string_table)


def test_discover_kernel_performance(parsed: Section) -> None:
    """Test kernel performance discovery function."""

    result = kernel.discover_kernel_performance(parsed)

    assert len(result) == 1
    assert result[0] == (None, {})


@time_machine.travel("2020-06-04 15:40:00")
def test_check_kernel_performance_no_params(
    parsed: Section, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test kernel performance check function without parameters."""

    # Pre-populate value store for rate calculations to avoid GetRateError
    base_time = 10000.0  # Base timestamp for rate calculations (before current 11238)
    value_store: dict[str, object] = {
        "ctxt": (base_time, 500000000),  # Previous context switches
        "processes": (base_time, 4500000),  # Previous process creations
        "pgmajfault": (base_time, 1750000),  # Previous major page faults
        "pswpin": (base_time, 240000),  # Previous page swap in
        "pswpout": (base_time, 720000),  # Previous page swap out
    }
    monkeypatch.setattr(kernel, "get_value_store", lambda: value_store)

    results = list(kernel.check_kernel_performance(None, {}, parsed))

    assert len(results) == 5

    # All results should be OK (state 0) without thresholds
    for result in results:
        state, summary, metrics = result
        assert state == 0
        assert "/s" in summary  # Should have rate info
        assert len(metrics) == 1
        assert metrics[0][1] > 0  # Rate should be positive
        assert len(metrics[0]) == 6  # Full metric tuple format

    # Verify we have the expected metrics
    metric_names = {result[2][0][0] for result in results}
    expected_metrics = {
        "process_creations",
        "context_switches",
        "major_page_faults",
        "page_swap_in",
        "page_swap_out",
    }
    assert metric_names == expected_metrics


@time_machine.travel("2020-06-04 15:40:00")
def test_check_kernel_performance_with_thresholds(
    parsed: tuple[float, Mapping[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test kernel performance check function with threshold parameters."""

    # Pre-populate value store for rate calculations
    base_time = 10000.0
    value_store: dict[str, object] = {
        "ctxt": (base_time, 500000000),
        "processes": (base_time, 4500000),
        "pgmajfault": (base_time, 1750000),
        "pswpin": (base_time, 240000),
        "pswpout": (base_time, 720000),
    }
    monkeypatch.setattr(kernel, "get_value_store", lambda: value_store)

    params = {
        "ctxt": (30000.0, 45000.0),
        "processes": (400.0, 500.0),
        "page_swap_in_levels": (10.0, 50.0),
        "page_swap_out_levels_lower": (500.0, 100.0),
    }

    results = list(kernel.check_kernel_performance(None, params, parsed))

    assert len(results) == 5

    # With threshold settings, we expect some results to be in warning/critical state
    warning_or_critical_found = False
    for result in results:
        state, summary, metrics = result
        assert state in [0, 1, 2]  # OK, WARN, or CRIT
        assert "/s" in summary
        assert len(metrics) == 1
        assert metrics[0][1] > 0  # Rate should be positive
        if state in [1, 2]:
            warning_or_critical_found = True
            assert "warn/crit" in summary  # Should show thresholds

    # At least one metric should trigger warning/critical with these thresholds
    assert warning_or_critical_found


def test_check_kernel_performance_no_timestamp() -> None:
    assert not list(kernel.check_kernel_performance(None, {}, (None, {})))


@time_machine.travel("2020-06-04 15:40:00")
def test_check_kernel_performance_missing_counters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test kernel performance check function with missing counters."""

    # Create parsed data with minimal counters
    minimal_parsed = (11238.0, {"Context Switches": [("ctxt", 539210403)]})

    # Pre-populate value store
    base_time = 10000.0
    value_store: dict[str, object] = {"ctxt": (base_time, 500000000)}
    monkeypatch.setattr(kernel, "get_value_store", lambda: value_store)

    results = list(kernel.check_kernel_performance(None, {}, minimal_parsed))

    # Should only get results for available counters
    assert len(results) == 1

    state, summary, metrics = results[0]
    assert state == 0
    assert "Context Switches:" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "context_switches"


@time_machine.travel("1970-01-01 00:00:00")
def test_check_kernel_performance_counter_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test kernel performance check function with missing counters."""

    # Create parsed data with minimal counters
    minimal_parsed = (11238.0, {"Context Switches": [("ctxt", 0)]})

    # Pre-populate value store
    base_time = -60.0
    value_store: dict[str, object] = {"ctxt": (base_time, 500000000)}
    monkeypatch.setattr(kernel, "get_value_store", lambda: value_store)

    with pytest.raises(GetRateError):
        _ = list(kernel.check_kernel_performance(None, {}, minimal_parsed))


def test_kernel_parse_function_empty() -> None:
    """Test kernel parse function with empty data."""
    string_table: list[list[str]] = []
    timestamp, items = parse_kernel(string_table)

    assert timestamp is None
    assert items == {}


def test_discover_kernel_performance_no_data() -> None:
    assert not list(kernel.discover_kernel_performance((11238.0, {})))
