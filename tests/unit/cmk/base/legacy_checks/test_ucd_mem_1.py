#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

from cmk.base.legacy_checks.ucd_mem import check_ucd_mem, discover_ucd_mem
from cmk.plugins.collection.agent_based.ucd_mem import parse_ucd_mem


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


def test_ucd_mem_1_discovery():
    """Test ucd_mem discovery."""
    services = list(discover_ucd_mem(parsed()))

    assert len(services) == 1
    assert services == [(None, {})]


def test_ucd_mem_1_check():
    """Test ucd_mem check."""
    params = {"levels_ram": (80.0, 90.0)}
    result = list(check_ucd_mem(None, params, parsed()))

    assert len(result) == 3

    # Check RAM result
    state, message, metrics = result[0]
    assert state == 0
    assert "RAM:" in message
    assert "78.09%" in message
    assert "47.9 GiB of 61.3 GiB" in message
    assert ("mem_used", 51426668544, None, None, 0, 65857241088) in metrics
    assert ("mem_used_percent", 78.08810040384546, None, None, 0.0, None) in metrics

    # Check Swap result
    state, message, metrics = result[1]
    assert state == 0
    assert "Swap:" in message
    assert "0% - 0 B of 8.00 GiB" in message
    assert ("swap_used", 0, None, None, 0, 8589930496) in metrics

    # Check Total virtual memory result
    state, message = result[2][:2]
    assert state == 0
    assert "Total virtual memory:" in message
    assert "69.08%" in message
    assert "47.9 GiB of 69.3 GiB" in message
