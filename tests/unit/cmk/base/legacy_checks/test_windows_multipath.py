#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from typing import Any

import pytest

from cmk.base.legacy_checks.windows_multipath import (
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
        ([["4"]], [(None, {"active_paths": 4})]),
        # Test data with different path count
        ([["8"]], [(None, {"active_paths": 8})]),
        # Test data with zero paths (should not discover)
        ([["0"]], []),
    ],
)
def test_discover_windows_multipath(info: list[list[str]], expected_discoveries: list[Any]) -> None:
    """Test discovery function for windows_multipath check."""
    parsed = parse_windows_multipath(info)
    result = list(discover_windows_multipath(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        # Test normal operation with default parameters
        (None, {"active_paths": 4}, [["4"]], [(0, "Paths active: 4"), (0, "Expected paths: 4")]),
        # Test with more paths than expected (warning)
        (
            None,
            {"active_paths": 4},
            [["6"]],
            [(0, "Paths active: 6"), (0, "Expected paths: 4"), (1, "(warn at 4)")],
        ),
        # Test with fewer paths than expected (critical)
        (
            None,
            {"active_paths": 4},
            [["2"]],
            [(0, "Paths active: 2"), (0, "Expected paths: 4"), (2, "(crit below 4)")],
        ),
        # Test with percentage-based thresholds (warning condition)
        (
            None,
            {"active_paths": (8, 75, 50)},  # 8 paths total, 75% warn, 50% crit
            [["4"]],
            [(0, "Paths active: 4"), (1, "(warn/crit below 6/4)")],
        ),
        # Test with percentage-based thresholds in warning range
        (
            None,
            {"active_paths": (8, 75, 50)},  # 8 paths total, 75% warn, 50% crit
            [["5"]],
            [(0, "Paths active: 5"), (1, "(warn/crit below 6/4)")],
        ),
        # Test with percentage-based thresholds in OK range
        (
            None,
            {"active_paths": (8, 75, 50)},  # 8 paths total, 75% warn, 50% crit
            [["7"]],
            [(0, "Paths active: 7")],
        ),
    ],
)
def test_check_windows_multipath(
    item: Any, params: dict[str, Any], info: list[list[str]], expected_results: list[Any]
) -> None:
    """Test check function for windows_multipath check."""
    parsed = parse_windows_multipath(info)
    result = list(check_windows_multipath(item, params, parsed))
    assert result == expected_results
