#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.pulse_secure_mem_util import (
    check_pulse_secure_mem,
    discover_pulse_secure_mem_util,
    parse_pulse_secure_mem,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([["8", "0"]], [(None, {})]),
    ],
)
def test_discover_pulse_secure_mem(
    info: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for pulse_secure_mem_util check."""
    parsed = parse_pulse_secure_mem(info)
    if parsed is not None:
        result = list(discover_pulse_secure_mem_util(parsed))
    else:
        result = []
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            None,
            {"mem_used_percent": (90, 95), "swap_used_percent": (5, None)},
            [["8", "0"]],
            [
                (0, "RAM used: 8.00%", [("mem_used_percent", 8, 90.0, 95.0)]),
                (0, "Swap used: 0%", [("swap_used_percent", 0, 5.0, None)]),
            ],
        ),
    ],
)
def test_check_pulse_secure_mem(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for pulse_secure_mem_util check."""
    parsed = parse_pulse_secure_mem(info)
    result = list(check_pulse_secure_mem(item, params, parsed))
    assert result == expected_results
