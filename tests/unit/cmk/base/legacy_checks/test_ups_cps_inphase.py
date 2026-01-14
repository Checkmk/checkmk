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
from cmk.base.check_legacy_includes.elphase import check_elphase as check_ups_cps_inphase
from cmk.base.legacy_checks.ups_cps_inphase import discover_ups_cps_inphase, parse_ups_cps_inphase


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["32", "NULL"]], [("1", {})]),
    ],
)
def test_discover_ups_cps_inphase(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ups_cps_inphase check."""
    parsed = parse_ups_cps_inphase(string_table)
    result = list(discover_ups_cps_inphase(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        ("1", {}, [["32", "NULL"]], [(0, "Voltage: 3.2 V", [("voltage", 3.2, None, None)])]),
    ],
)
def test_check_ups_cps_inphase(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ups_cps_inphase check."""
    parsed = parse_ups_cps_inphase(string_table)
    assert parsed
    result = list(check_ups_cps_inphase(item, params, parsed))
    assert result == expected_results
