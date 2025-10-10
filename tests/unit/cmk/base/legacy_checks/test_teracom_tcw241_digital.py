#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.teracom_tcw241_digital import (
    check_tcw241_digital,
    discover_teracom_tcw241_digital,
    parse_tcw241_digital,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                [["Tank_Status", "NEA_Status", "Digital Input 3", "Digital Input 4"]],
                [["1", "1", "1", "1"]],
            ],
            [("4", {}), ("3", {}), ("2", {}), ("1", {})],
        ),
    ],
)
def test_discover_teracom_tcw241_digital(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for teracom_tcw241_digital check."""
    parsed = parse_tcw241_digital(info)
    result = list(discover_teracom_tcw241_digital(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "4",
            {},
            [
                [["Tank_Status", "NEA_Status", "Digital Input 3", "Digital Input 4"]],
                [["1", "1", "1", "1"]],
            ],
            [(0, "[Digital Input 4] is open")],
        ),
        (
            "3",
            {},
            [
                [["Tank_Status", "NEA_Status", "Digital Input 3", "Digital Input 4"]],
                [["1", "1", "1", "1"]],
            ],
            [(0, "[Digital Input 3] is open")],
        ),
        (
            "2",
            {},
            [
                [["Tank_Status", "NEA_Status", "Digital Input 3", "Digital Input 4"]],
                [["1", "1", "1", "1"]],
            ],
            [(0, "[NEA_Status] is open")],
        ),
        (
            "1",
            {},
            [
                [["Tank_Status", "NEA_Status", "Digital Input 3", "Digital Input 4"]],
                [["1", "1", "1", "1"]],
            ],
            [(0, "[Tank_Status] is open")],
        ),
    ],
)
def test_check_teracom_tcw241_digital(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for teracom_tcw241_digital check."""
    parsed = parse_tcw241_digital(info)
    result = list(check_tcw241_digital(item, params, parsed))
    assert result == expected_results
