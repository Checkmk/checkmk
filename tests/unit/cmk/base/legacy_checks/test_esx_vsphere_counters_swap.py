#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.esx_vsphere_counters import (
    check_esx_vsphere_counters_swap,
    inventory_esx_vsphere_counters_swap,
)
from cmk.plugins.vsphere.agent_based.esx_vsphere_counters import parse_esx_vsphere_counters
from cmk.plugins.vsphere.lib.esx_vsphere import SectionCounter


@pytest.fixture(name="esx_vsphere_counters_swap_string_table")
def _esx_vsphere_counters_swap_string_table() -> StringTable:
    """ESX vSphere counters swap data."""
    return [
        ["mem.swapin", "", "0", "kiloBytes"],
        ["mem.swapout", "", "", "kiloBytes"],
        ["mem.swapused", "", "0", "kiloBytes"],
    ]


@pytest.fixture(name="esx_vsphere_counters_swap_parsed")
def _esx_vsphere_counters_swap_parsed(
    esx_vsphere_counters_swap_string_table: StringTable,
) -> SectionCounter:
    """Parsed ESX vSphere counters swap data."""
    return parse_esx_vsphere_counters(esx_vsphere_counters_swap_string_table)


def test_inventory_esx_vsphere_counters_swap(
    esx_vsphere_counters_swap_parsed: SectionCounter,
) -> None:
    """Test discovery function for ESX vSphere counters swap check."""
    result = list(inventory_esx_vsphere_counters_swap(esx_vsphere_counters_swap_parsed))
    assert result == [(None, {})]


def test_inventory_esx_vsphere_counters_swap_no_data() -> None:
    """Test discovery function with no swap data."""
    parsed = parse_esx_vsphere_counters([])
    result = list(inventory_esx_vsphere_counters_swap(parsed))
    assert result == []


def test_inventory_esx_vsphere_counters_swap_all_empty() -> None:
    """Test discovery function with all empty swap values."""
    string_table = [
        ["mem.swapin", "", "", "kiloBytes"],
        ["mem.swapout", "", "", "kiloBytes"],
        ["mem.swapused", "", "", "kiloBytes"],
    ]
    parsed = parse_esx_vsphere_counters(string_table)
    result = list(inventory_esx_vsphere_counters_swap(parsed))
    assert result == []


def test_check_esx_vsphere_counters_swap(
    esx_vsphere_counters_swap_parsed: SectionCounter,
) -> None:
    """Test check function for ESX vSphere counters swap."""
    result = list(check_esx_vsphere_counters_swap(None, {}, esx_vsphere_counters_swap_parsed))
    expected = [
        (0, "Swap in: 0 B"),
        (0, "Swap out: not available"),
        (0, "Swap used: 0 B"),
    ]
    assert result == expected


def test_check_esx_vsphere_counters_swap_with_values() -> None:
    """Test check function with actual swap values."""
    string_table = [
        ["mem.swapin", "", "1024", "kiloBytes"],
        ["mem.swapout", "", "2048", "kiloBytes"],
        ["mem.swapused", "", "512", "kiloBytes"],
    ]
    parsed = parse_esx_vsphere_counters(string_table)
    result = list(check_esx_vsphere_counters_swap(None, {}, parsed))
    expected = [
        (0, "Swap in: 1.00 KiB"),
        (0, "Swap out: 2.00 KiB"),
        (0, "Swap used: 512 B"),
    ]
    assert result == expected


def test_check_esx_vsphere_counters_swap_missing_data() -> None:
    """Test check function with missing swap data."""
    string_table = [
        ["mem.swapin", "", "1024", "kiloBytes"],
        # mem.swapout missing
        ["mem.swapused", "", "", "kiloBytes"],  # empty value
    ]
    parsed = parse_esx_vsphere_counters(string_table)
    result = list(check_esx_vsphere_counters_swap(None, {}, parsed))
    expected = [
        (0, "Swap in: 1.00 KiB"),
        (0, "Swap out: not available"),
        (0, "Swap used: not available"),
    ]
    assert result == expected


def test_check_esx_vsphere_counters_swap_large_values() -> None:
    """Test check function with large swap values."""
    string_table = [
        ["mem.swapin", "", "1048576", "kiloBytes"],  # 1 GB
        ["mem.swapout", "", "2097152", "kiloBytes"],  # 2 GB
        ["mem.swapused", "", "524288", "kiloBytes"],  # 512 MB
    ]
    parsed = parse_esx_vsphere_counters(string_table)
    result = list(check_esx_vsphere_counters_swap(None, {}, parsed))
    expected = [
        (0, "Swap in: 1.00 MiB"),
        (0, "Swap out: 2.00 MiB"),
        (0, "Swap used: 512 KiB"),
    ]
    assert result == expected


def test_check_esx_vsphere_counters_swap_no_counters() -> None:
    """Test check function with no counter data at all."""
    parsed = parse_esx_vsphere_counters([])
    result = list(check_esx_vsphere_counters_swap(None, {}, parsed))
    expected = [
        (0, "Swap in: not available"),
        (0, "Swap out: not available"),
        (0, "Swap used: not available"),
    ]
    assert result == expected
