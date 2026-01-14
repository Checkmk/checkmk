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
from cmk.base.legacy_checks.f5_bigip_psu import (
    check_f5_bigip_psu,
    discover_f5_bigip_psu,
    parse_f5_bigip_psu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1", "1"], ["2", "1"]], [("1", None), ("2", None)]),
    ],
)
def test_discover_f5_bigip_psu(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for f5_bigip_psu check."""
    parsed = parse_f5_bigip_psu(string_table)
    result = list(discover_f5_bigip_psu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        ("1", {}, [["1", "1"], ["2", "1"]], [0, "PSU state: good"]),
        ("2", {}, [["1", "1"], ["2", "1"]], [0, "PSU state: good"]),
    ],
)
def test_check_f5_bigip_psu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for f5_bigip_psu check."""
    parsed = parse_f5_bigip_psu(string_table)
    result = list(check_f5_bigip_psu(item, params, parsed))
    assert result == expected_results
