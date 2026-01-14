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
from cmk.base.legacy_checks.ups_cps_battery import (
    check_ups_cps_battery,
    discover_ups_cps_battery,
    parse_ups_cps_battery,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["73", "41", "528000"]], [(None, {})]),
    ],
)
def test_discover_ups_cps_battery(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ups_cps_battery check."""
    parsed = parse_ups_cps_battery(string_table)
    result = list(discover_ups_cps_battery(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"capacity": (95, 90)},
            [["73", "41", "528000"]],
            [(2, "Capacity at 73% (warn/crit at 95/90%)"), (0, "88 minutes remaining on battery")],
        ),
    ],
)
def test_check_ups_cps_battery(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ups_cps_battery check."""
    parsed = parse_ups_cps_battery(string_table)
    result = list(check_ups_cps_battery(item, params, parsed))
    assert result == expected_results
