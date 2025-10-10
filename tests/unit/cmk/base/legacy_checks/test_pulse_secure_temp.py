#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.pulse_secure_temp import (
    check_pulse_secure_temp,
    discover_pulse_secure_temp,
    parse_pulse_secure_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["27"]], [("IVE", {})]),
    ],
)
def test_discover_pulse_secure_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for pulse_secure_temp check."""
    parsed = parse_pulse_secure_temp(string_table)
    result = list(discover_pulse_secure_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        ("IVE", {"levels": (70.0, 75.0)}, [["27"]], [0, "27 °C", [("temp", 27, 70.0, 75.0)]]),
    ],
)
def test_check_pulse_secure_temp(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for pulse_secure_temp check."""
    parsed = parse_pulse_secure_temp(string_table)
    result = list(check_pulse_secure_temp(item, params, parsed))
    assert result == expected_results
