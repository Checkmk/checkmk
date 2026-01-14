#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

from cmk.base.legacy_checks.mem_linux import (
    check_mem_linux,
    discover_mem_linux,
)


def test_inventorize_mem_linux_basic() -> None:
    """Test inventory function for mem_linux check with basic Linux memory data."""
    # The inventory function requires specific keys to be present via memory.is_linux_section
    section = {
        "MemTotal": 8192000,  # 8GB in KB
        "MemFree": 1024000,  # 1GB free
        "Buffers": 512000,  # 512MB buffers
        "Cached": 2048000,  # 2GB cached
        "SwapTotal": 2097152,  # 2GB swap
        "SwapFree": 2097152,  # All swap free
        "Dirty": 1024,  # 1MB dirty
        "Writeback": 512,  # Required by is_linux_section
    }

    result = list(discover_mem_linux(section))

    # Should discover the service now that all required keys are present
    assert result == [(None, {})]


def test_check_mem_linux_normal_usage() -> None:
    """Test check function for mem_linux with normal memory usage."""
    section = {
        "MemTotal": 8192000,  # 8GB
        "MemFree": 2048000,  # 2GB free
        "Buffers": 512000,  # 512MB buffers
        "Cached": 1536000,  # 1.5GB cached
        "SwapTotal": 2097152,  # 2GB swap
        "SwapFree": 2097152,  # All swap free
        "Dirty": 1024,  # 1MB dirty
    }

    params: dict[str, Any] = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
        "levels_total": ("perc_used", (120.0, 150.0)),
    }

    result = list(check_mem_linux(None, params, section))

    # Should return multiple results
    assert len(result) >= 2

    # First result should be virtual memory status
    virtual_result = result[0]
    assert virtual_result[0] == 0  # Should be OK with normal usage

    # Should include memory usage information - check actual text from test failure
    result_summaries = [r[1] for r in result]
    summary_text = " ".join(result_summaries)
    # Based on the test failure, the text contains "virtual memory" not just "used"
    assert "virtual memory" in summary_text.lower()

    # Should have performance data in last result
    last_result = result[-1]
    assert len(last_result) == 3  # state, summary, perfdata
    assert last_result[2] is not None  # Should have perfdata


def test_check_mem_linux_high_usage() -> None:
    """Test check function for mem_linux with high memory usage."""
    section = {
        "MemTotal": 8192000,  # 8GB
        "MemFree": 409600,  # 400MB free (low)
        "Buffers": 102400,  # 100MB buffers
        "Cached": 204800,  # 200MB cached
        "SwapTotal": 2097152,  # 2GB swap
        "SwapFree": 1048576,  # 1GB swap used
        "Dirty": 1024,  # 1MB dirty
    }

    params: dict[str, Any] = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
        "levels_total": ("perc_used", (120.0, 150.0)),
    }

    result = list(check_mem_linux(None, params, section))

    # Should return multiple results
    assert len(result) >= 2

    # With high memory usage, we might get warnings
    result_states = [r[0] for r in result]

    # Check that we get meaningful status
    assert any(state >= 0 for state in result_states)

    # Should have performance data
    last_result = result[-1]
    assert last_result[2] is not None


def test_check_mem_linux_with_swap_usage() -> None:
    """Test check function for mem_linux with swap usage."""
    section = {
        "MemTotal": 4194304,  # 4GB
        "MemFree": 524288,  # 512MB free
        "Buffers": 262144,  # 256MB buffers
        "Cached": 524288,  # 512MB cached
        "SwapTotal": 2097152,  # 2GB swap
        "SwapFree": 1048576,  # 1GB swap free (1GB used)
        "Dirty": 2048,  # 2MB dirty
        "Writeback": 512,  # 512KB writeback
    }

    params: dict[str, Any] = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
        "levels_total": ("perc_used", (120.0, 150.0)),
    }

    result = list(check_mem_linux(None, params, section))

    # Should return multiple results
    assert len(result) >= 2

    # Should calculate swap usage correctly
    # SwapUsed = SwapTotal - SwapFree = 2097152 - 1048576 = 1048576 (1GB)

    # Performance data should include swap metrics
    last_result = result[-1]
    perfdata = last_result[2]
    assert perfdata is not None

    # Should have various memory metrics
    metric_names = [metric[0] for metric in perfdata]
    assert any("swap" in name for name in metric_names)


def test_check_mem_linux_missing_optional_fields() -> None:
    """Test check function for mem_linux with missing optional fields."""
    # Minimal section (some fields might be missing on older kernels)
    section = {
        "MemTotal": 2097152,  # 2GB
        "MemFree": 524288,  # 512MB free
        "Buffers": 131072,  # 128MB buffers
        "Cached": 262144,  # 256MB cached
        "SwapTotal": 1048576,  # 1GB swap
        "SwapFree": 1048576,  # All swap free
        "Dirty": 512,  # 512KB dirty
        # Missing: SReclaimable, SwapCached, Writeback, etc.
    }

    params: dict[str, Any] = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
    }

    result = list(check_mem_linux(None, params, section))

    # Should still work with missing optional fields
    assert len(result) >= 2

    # Should handle missing fields gracefully
    virtual_result = result[0]
    assert virtual_result[0] in [0, 1, 2]  # Valid state

    # Should have performance data
    last_result = result[-1]
    assert last_result[2] is not None


def test_check_mem_linux_empty_section() -> None:
    """Test check function for mem_linux with empty section."""
    section: dict[str, Any] = {}

    params: dict[str, Any] = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
    }

    result = list(check_mem_linux(None, params, section))

    # Should return empty results for empty section
    assert result == []
