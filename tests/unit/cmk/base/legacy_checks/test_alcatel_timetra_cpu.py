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
from cmk.base.legacy_checks.alcatel_timetra_cpu import (
    check_alcatel_timetra_cpu,
    discover_alcatel_timetra_cpu,
    parse_alcatel_timetra_cpu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["92"]], [(None, {})]),
    ],
)
def test_discover_alcatel_timetra_cpu(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for alcatel_timetra_cpu check."""
    parsed = parse_alcatel_timetra_cpu(string_table)
    result = list(discover_alcatel_timetra_cpu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            (90.0, 95.0),
            [["92"]],
            [
                (
                    1,
                    "Total CPU: 92.00% (warn/crit at 90.00%/95.00%)",
                    [("util", 92, 90.0, 95.0, 0, 100)],
                )
            ],
        ),
    ],
)
def test_check_alcatel_timetra_cpu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for alcatel_timetra_cpu check."""
    parsed = parse_alcatel_timetra_cpu(string_table)
    result = list(check_alcatel_timetra_cpu(item, params, parsed))
    assert result == expected_results
