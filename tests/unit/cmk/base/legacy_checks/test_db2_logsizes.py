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
from cmk.base.legacy_checks.db2_logsizes import (
    check_db2_logsizes,
    discover_db2_logsizes,
    parse_db2_logsizes,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["[[[db2mpss:ASMPROD]]]"],
                ["TIMESTAMP", "1474466290"],
                ["usedspace", "2204620"],
                ["logfilsiz", "2000"],
                ["logprimary", "5"],
                ["logsecond", "20"],
            ],
            [("db2mpss:ASMPROD", {})],
        ),
    ],
)
def test_discover_db2_logsizes(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for db2_logsizes check."""
    parsed = parse_db2_logsizes(string_table)
    result = list(discover_db2_logsizes(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "db2mpss:ASMPROD",
            {"levels": (-20.0, -10.0)},
            [
                ["[[[db2mpss:ASMPROD]]]"],
                ["TIMESTAMP", "1474466290"],
                ["usedspace", "-"],
                ["logfilsiz", "2000"],
                ["logprimary", "5"],
                ["logsecond", "20"],
            ],
            (
                3,
                "Can not read usedspace",
            ),
        ),
        (
            "db2mpss:ASMPROD",
            {"levels": (-20.0, -10.0)},
            [
                ["[[[db2mpss:ASMPROD]]]"],
                ["TIMESTAMP", "1474466290"],
                ["usedspace", "2204620"],
                ["logfilsiz", "2000"],
                ["logprimary", "5"],
                ["logsecond", "20"],
            ],
            (
                0,
                "Used: 1.03% - 2.00 MiB of 195 MiB",
                [
                    ("fs_used", 2.0, 156.0, 175.5, 0.0, 195.0),
                    ("fs_free", 193.0, None, None, 0.0, None),
                    ("fs_used_percent", 1.0256410256410255, 80.0, 90.0, 0.0, 100.0),
                    ("fs_size", 195, None, None, 0, None),
                ],
            ),
        ),
    ],
)
def test_check_db2_logsizes(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for db2_logsizes check."""
    parsed = parse_db2_logsizes(string_table)
    result = check_db2_logsizes(item, params, parsed)
    assert result == expected_results
