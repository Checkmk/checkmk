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
from cmk.base.legacy_checks.md import check_md, discover_md, parse_md


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["Personalities", ":", "[linear]", "[raid0]", "[raid1]"],
                ["md1", ":", "active", "linear", "sda3[0]", "sdb3[1]"],
                ["491026496", "blocks", "64k", "rounding"],
                ["md0", ":", "active", "raid0", "sda2[0]", "sdb2[1]"],
                ["2925532672", "blocks", "64k", "chunks"],
                ["unused", "devices:", "<none>"],
            ],
            [("md1", None)],
        ),
    ],
)
def test_discover_md(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for md check."""
    parsed = parse_md(string_table)
    result = list(discover_md(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "md1",
            {},
            [
                ["Personalities", ":", "[linear]", "[raid0]", "[raid1]"],
                ["md1", ":", "active", "linear", "sda3[0]", "sdb3[1]"],
                ["491026496", "blocks", "64k", "rounding"],
                ["md0", ":", "active", "raid0", "sda2[0]", "sdb2[1]"],
                ["2925532672", "blocks", "64k", "chunks"],
                ["unused", "devices:", "<none>"],
            ],
            [(0, "Status: active"), (0, "Spare: 0, Failed: 0, Active: 2")],
        ),
    ],
)
def test_check_md(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for md check."""
    parsed = parse_md(string_table)
    result = list(check_md(item, params, parsed))
    assert result == expected_results
