#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.mem_linux import check_mem_linux, discover_mem_linux


@pytest.fixture
def section() -> Mapping[str, int]:
    """Create Linux memory section data based on dataset."""
    return {
        "MemTotal": 25300574208,
        "MemFree": 451813376,
        "Buffers": 328368128,
        "Cached": 20460552192,
        "SwapCached": 6320128,
        "Active": 8967041024,
        "Inactive": 13681094656,
        "Active(anon)": 1516785664,
        "Inactive(anon)": 380170240,
        "Active(file)": 7450255360,
        "Inactive(file)": 13300924416,
        "Unevictable": 987963392,
        "Mlocked": 987963392,
        "SwapTotal": 17179865088,
        "SwapFree": 17104207872,
        "Dirty": 4513918976,
        "Writeback": 38932480,
        "AnonPages": 2841030656,
        "Mapped": 71122944,
        "Shmem": 34582528,
        "Slab": 881692672,
        "SReclaimable": 774385664,
        "SUnreclaim": 107307008,
        "KernelStack": 4276224,
        "PageTables": 16273408,
        "NFS_Unstable": 0,
        "Bounce": 0,
        "WritebackTmp": 0,
        "CommitLimit": 39950381056,
        "Committed_AS": 3624763392,
        "VmallocTotal": 35184372087808,
        "VmallocUsed": 356253696,
        "VmallocChunk": 0,  # This is the key feature for this regression test
        "HardwareCorrupted": 6144,
        "AnonHugePages": 0,
        "HugePages_Total": 0,
        "HugePages_Free": 0,
        "HugePages_Rsvd": 0,
        "HugePages_Surp": 0,
        "Hugepagesize": 2097152,
        "DirectMap4k": 274726912,
        "DirectMap2M": 8306819072,
        "DirectMap1G": 17179869184,
    }


def test_mem_linux_discovery(section: Mapping[str, int]) -> None:
    """Test Linux memory discovery function."""
    assert list(discover_mem_linux(section)) == [Service()]


def test_mem_linux_check_vmalloc_chunk_regression(section: Mapping[str, int]) -> None:
    """Test Linux memory check function with VmallocChunk=0 regression scenario."""
    params = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
        "levels_total": ("perc_used", (120.0, 150.0)),
        "levels_shm": ("perc_used", (20.0, 30.0)),
        "levels_pagetables": ("perc_used", (8.0, 16.0)),
        "levels_committed": ("perc_used", (100.0, 150.0)),
        "levels_commitlimit": ("perc_free", (20.0, 10.0)),
        "levels_vmalloc": ("abs_free", (52428800, 31457280)),
        "levels_hardwarecorrupted": ("abs_used", (1, 1)),
    }

    result = list(check_mem_linux(params, section))
    text_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]

    # Should have multiple result entries
    assert len(text_results) >= 8

    # First result should be virtual memory status
    assert text_results[0].state == State.OK
    assert "Total virtual memory" in text_results[0].summary
    assert "7.90%" in text_results[0].summary

    # Look for hardware corrupted result (should be critical due to levels)
    hardware_corrupted = next(
        (r for r in text_results if "Hardware Corrupted" in r.details),
        None,
    )
    assert hardware_corrupted is not None, "Hardware Corrupted result not found"
    assert hardware_corrupted.state == State.CRIT
    assert "warn/crit at 1 B/1 B used" in hardware_corrupted.details

    # Check that RAM usage is reported
    ram_result = next(
        (r for r in text_results if "RAM:" in r.details and "12.96%" in r.details),
        None,
    )
    assert ram_result is not None, "RAM usage result not found"
    assert ram_result.state == State.OK
    assert "3.05 GiB of 23.6 GiB" in ram_result.details

    # Check that swap usage is reported
    swap_result = next(
        (r for r in text_results if "Swap:" in r.details and "0.44%" in r.details),
        None,
    )
    assert swap_result is not None, "Swap usage result not found"
    assert swap_result.state == State.OK
    assert "72.2 MiB of 16.0 GiB" in swap_result.details

    # Check result contains extensive performance data
    assert len(metrics) > 30


def test_mem_linux_check_without_vmalloc_threshold(section: Mapping[str, int]) -> None:
    """Test Linux memory check function without vmalloc threshold params."""
    params = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
        "levels_shm": ("perc_used", (20.0, 30.0)),
        "levels_pagetables": ("perc_used", (8.0, 16.0)),
        "levels_committed": ("perc_used", (100.0, 150.0)),
        "levels_commitlimit": ("perc_free", (20.0, 10.0)),
        "levels_vmalloc": ("abs_free", (52428800, 31457280)),
        "levels_hardwarecorrupted": ("abs_used", (1, 1)),
    }

    result = list(check_mem_linux(params, section))
    text_results = [r for r in result if isinstance(r, Result)]

    # Should still work without levels_total param
    assert len(text_results) >= 8

    # First result should still be virtual memory status
    assert text_results[0].state == State.OK
    assert "Total virtual memory" in text_results[0].summary


def test_mem_linux_check_empty_section() -> None:
    """Test Linux memory check function with empty section."""
    assert list(check_mem_linux({}, {})) == []


def test_mem_linux_discovery_non_linux_section() -> None:
    """Test Linux memory discovery function with non-Linux section."""
    non_linux_section = {
        "MemTotal": 1000000,
        "MemFree": 500000,
        # Missing required keys for Linux section
    }

    assert list(discover_mem_linux(non_linux_section)) == []
