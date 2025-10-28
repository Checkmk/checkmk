#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Final

from cmk.agent_based.v2 import Result, Service, State
from cmk.base.legacy_checks.esx_vsphere_counters import (
    check_esx_vsphere_counters_swap,
    inventory_esx_vsphere_counters_swap,
)
from cmk.plugins.vsphere.agent_based.esx_vsphere_counters import parse_esx_vsphere_counters

_STRING_TABLE: Final = [
    ["mem.swapin", "", "0", "kiloBytes"],
    ["mem.swapout", "", "", "kiloBytes"],
    ["mem.swapused", "", "0", "kiloBytes"],
]


def test_inventory_esx_vsphere_counters_swap() -> None:
    """Test discovery function for ESX vSphere counters swap check."""
    assert list(inventory_esx_vsphere_counters_swap(parse_esx_vsphere_counters(_STRING_TABLE))) == [
        Service()
    ]


def test_inventory_esx_vsphere_counters_swap_no_data() -> None:
    """Test discovery function with no swap data."""
    assert not list(inventory_esx_vsphere_counters_swap(parse_esx_vsphere_counters([])))


def test_inventory_esx_vsphere_counters_swap_all_empty() -> None:
    """Test discovery function with all empty swap values."""
    string_table = [
        ["mem.swapin", "", "", "kiloBytes"],
        ["mem.swapout", "", "", "kiloBytes"],
        ["mem.swapused", "", "", "kiloBytes"],
    ]
    parsed = parse_esx_vsphere_counters(string_table)
    result = list(inventory_esx_vsphere_counters_swap(parsed))
    assert not result


def test_check_esx_vsphere_counters_swap() -> None:
    """Test check function for ESX vSphere counters swap."""
    assert list(check_esx_vsphere_counters_swap(parse_esx_vsphere_counters(_STRING_TABLE))) == [
        Result(state=State.OK, summary="Swap in: 0 B"),
        Result(state=State.OK, summary="Swap used: 0 B"),
    ]


def test_check_esx_vsphere_counters_swap_with_values() -> None:
    """Test check function with actual swap values."""
    assert list(
        check_esx_vsphere_counters_swap(
            parse_esx_vsphere_counters(
                [
                    ["mem.swapin", "", "2048", "kiloBytes"],
                    ["mem.swapout", "", "4096", "kiloBytes"],
                    ["mem.swapused", "", "1024", "kiloBytes"],
                ]
            )
        )
    ) == [
        Result(state=State.OK, summary="Swap in: 2.00 KiB"),
        Result(state=State.OK, summary="Swap out: 4.00 KiB"),
        Result(state=State.OK, summary="Swap used: 1.00 KiB"),
    ]


def test_check_esx_vsphere_counters_swap_missing_data() -> None:
    """Test check function with missing swap data."""
    assert list(
        check_esx_vsphere_counters_swap(
            parse_esx_vsphere_counters(
                [
                    ["mem.swapin", "", "1024", "kiloBytes"],
                    # mem.swapout missing
                    ["mem.swapused", "", "", "kiloBytes"],  # empty value
                ]
            )
        )
    ) == [
        Result(state=State.OK, summary="Swap in: 1.00 KiB"),
    ]


def test_check_esx_vsphere_counters_swap_no_counters() -> None:
    """Test check function with no counter data at all."""
    assert not list(check_esx_vsphere_counters_swap(parse_esx_vsphere_counters([])))
