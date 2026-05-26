#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.windows.agent_based.windows_multipath import (
    check_windows_multipath,
    discover_windows_multipath,
    parse_windows_multipath,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        # Test data from dataset - error condition, no discovery
        (
            [
                [
                    "C:\\Program",
                    "Files",
                    "(x86)\\check_mk\\plugins\\windows_multipath.ps1(19,",
                    "1)",
                    "(null):",
                    "0x80041010",
                ]
            ],
            [],
        ),
        # Test data with valid multipath count
        ([["4"]], [Service(parameters={"active_paths": 4})]),
        # Test data with different path count
        ([["8"]], [Service(parameters={"active_paths": 8})]),
        # Test data with zero paths (should not discover)
        ([["0"]], []),
    ],
)
def test_discover_windows_multipath(
    info: list[list[str]], expected_discoveries: list[Service]
) -> None:
    """Test discovery function for windows_multipath check."""
    parsed = parse_windows_multipath(info)
    result = list(discover_windows_multipath(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "params, info, expected_results",
    [
        # Test normal operation with default parameters
        (
            {"active_paths": 4},
            [["4"]],
            [
                Result(state=State.OK, summary="Paths active: 4"),
                Result(state=State.OK, summary="Expected paths: 4"),
            ],
        ),
        # Test with more paths than expected (warning)
        (
            {"active_paths": 4},
            [["6"]],
            [
                Result(state=State.OK, summary="Paths active: 6"),
                Result(state=State.OK, summary="Expected paths: 4"),
                Result(state=State.WARN, summary="(warn at 4)"),
            ],
        ),
        # Test with fewer paths than expected (critical)
        (
            {"active_paths": 4},
            [["2"]],
            [
                Result(state=State.OK, summary="Paths active: 2"),
                Result(state=State.OK, summary="Expected paths: 4"),
                Result(state=State.CRIT, summary="(crit below 4)"),
            ],
        ),
        # Test with percentage-based thresholds (warning condition)
        (
            {"active_paths": (8, 75, 50)},  # 8 paths total, 75% warn, 50% crit
            [["4"]],
            [
                Result(state=State.OK, summary="Paths active: 4"),
                Result(state=State.WARN, summary="(warn/crit below 6/4)"),
            ],
        ),
        # Test with percentage-based thresholds in warning range
        (
            {"active_paths": (8, 75, 50)},  # 8 paths total, 75% warn, 50% crit
            [["5"]],
            [
                Result(state=State.OK, summary="Paths active: 5"),
                Result(state=State.WARN, summary="(warn/crit below 6/4)"),
            ],
        ),
        # Test with percentage-based thresholds in OK range
        (
            {"active_paths": (8, 75, 50)},  # 8 paths total, 75% warn, 50% crit
            [["7"]],
            [Result(state=State.OK, summary="Paths active: 7")],
        ),
    ],
)
def test_check_windows_multipath(
    params: Mapping[str, Any], info: list[list[str]], expected_results: list[Result]
) -> None:
    """Test check function for windows_multipath check."""
    parsed = parse_windows_multipath(info)
    result = list(check_windows_multipath(params, parsed))
    assert result == expected_results
