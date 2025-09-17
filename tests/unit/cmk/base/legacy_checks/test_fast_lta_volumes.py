#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.fast_lta_volumes import (
    check_fast_lta_volumes,
    discover_fast_lta_volumes,
    parse_fast_lta_volumes,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["Archiv_Test", "1000000000000", "10000000000"], ["Archiv_Test_1", "", ""]],
            [("Archiv_Test", {})],
        ),
    ],
)
def test_discover_fast_lta_volumes(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for fast_lta_volumes check."""
    parsed = parse_fast_lta_volumes(string_table)
    result = list(discover_fast_lta_volumes(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Archiv_Test",
            {"levels": (80.0, 90.0)},
            [["Archiv_Test", "1000000000000", "10000000000"], ["Archiv_Test_1", "", ""]],
            [
                (
                    0,
                    "Used: 1.00% - 9.31 GiB of 931 GiB",
                    [
                        (
                            "fs_used",
                            9536.7431640625,
                            762939.453125,
                            858306.884765625,
                            0,
                            953674.31640625,
                        ),
                        ("fs_free", 944137.5732421875, None, None, 0, None),
                        ("fs_used_percent", 1.0, 80.0, 90.0, 0.0, 100.0),
                        ("fs_size", 953674.31640625, None, None, 0, None),
                    ],
                )
            ],
        ),
    ],
)
def test_check_fast_lta_volumes(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for fast_lta_volumes check."""
    parsed = parse_fast_lta_volumes(string_table)
    result = list(check_fast_lta_volumes(item, params, parsed))
    assert result == expected_results
