#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.memory.agent_based.mem_linux import (
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

    assert list(discover_mem_linux(section)) == [Service()]


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

    result = list(check_mem_linux(params, section))
    text_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]

    # Should return multiple results
    assert len(text_results) >= 2

    # First result should be virtual memory status
    assert text_results[0].state == State.OK
    assert "Total virtual memory" in text_results[0].summary

    # Should have performance data
    assert metrics


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

    result = list(check_mem_linux(params, section))
    text_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]

    # Should return multiple results
    assert len(text_results) >= 2

    # Should have performance data
    assert metrics


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

    result = list(check_mem_linux(params, section))

    # Performance data should include swap metrics
    metric_names = {m.name for m in result if isinstance(m, Metric)}
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

    result = list(check_mem_linux(params, section))
    text_results = [r for r in result if isinstance(r, Result)]
    metrics = [r for r in result if isinstance(r, Metric)]

    # Should still work with missing optional fields
    assert len(text_results) >= 2

    # Should handle missing fields gracefully
    assert text_results[0].state in (State.OK, State.WARN, State.CRIT)

    # Should have performance data
    assert metrics


def test_check_mem_linux_empty_section() -> None:
    """Test check function for mem_linux with empty section."""
    section: dict[str, Any] = {}

    params: dict[str, Any] = {
        "levels_virtual": ("perc_used", (80.0, 90.0)),
    }

    assert list(check_mem_linux(params, section)) == []
