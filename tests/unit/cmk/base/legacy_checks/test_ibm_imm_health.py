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
from cmk.base.legacy_checks.ibm_imm_health import (
    check_ibm_imm_health,
    discover_ibm_imm_health,
    parse_ibm_imm_health,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["223523"], ["2342"], ["234"], ["23352"]], [(None, None)]),
    ],
)
def test_discover_ibm_imm_health(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ibm_imm_health check."""
    parsed = parse_ibm_imm_health(string_table)
    result = list(discover_ibm_imm_health(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (None, {}, [["223523"], ["2342"], ["234"], ["23352"]], [3, "23352(234)"]),
    ],
)
def test_check_ibm_imm_health(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ibm_imm_health check."""
    parsed = parse_ibm_imm_health(string_table)
    result = list(check_ibm_imm_health(item, params, parsed))
    assert result == expected_results
