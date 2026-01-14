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
from cmk.base.legacy_checks.tplink_cpu import (
    check_tplink_cpu,
    discover_tplink_cpu,
    parse_tplink_cpu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["21"]], [(None, {})]),
    ],
)
def test_discover_tplink_cpu(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for tplink_cpu check."""
    parsed = parse_tplink_cpu(string_table)
    result = list(discover_tplink_cpu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (None, {}, [["21"]], [(0, "Total CPU: 21.00%", [("util", 21.0, None, None, 0, 100)])]),
    ],
)
def test_check_tplink_cpu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for tplink_cpu check."""
    parsed = parse_tplink_cpu(string_table)
    result = list(check_tplink_cpu(item, params, parsed))
    assert result == expected_results
