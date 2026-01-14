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
from cmk.base.legacy_checks.pulse_secure_cpu_util import (
    check_pulse_secure_cpu,
    discover_pulse_secure_cpu_util,
    parse_pulse_secure_cpu_util,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([["1"]], [(None, {})]),
    ],
)
def test_discover_pulse_secure_cpu(
    info: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for pulse_secure_cpu_util check."""
    parsed = parse_pulse_secure_cpu_util(info)
    if parsed is not None:
        result = list(discover_pulse_secure_cpu_util(parsed))
    else:
        result = []
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"util": (80.0, 90.0)},
            [["1"]],
            [(0, "Total CPU: 1.00%", [("util", 1, 80.0, 90.0, 0, 100)])],
        ),
    ],
)
def test_check_pulse_secure_cpu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for pulse_secure_cpu_util check."""
    parsed = parse_pulse_secure_cpu_util(string_table)
    result = list(check_pulse_secure_cpu(item, params, parsed))
    assert result == expected_results
