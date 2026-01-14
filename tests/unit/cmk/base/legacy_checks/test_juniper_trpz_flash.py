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
from cmk.base.legacy_checks.juniper_trpz_flash import (
    check_juniper_trpz_flash,
    discover_juniper_trpz_flash,
    parse_juniper_trpz_flash,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["51439616", "62900224"]], [(None, {})]),
    ],
)
def test_discover_juniper_trpz_flash(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for juniper_trpz_flash check."""
    parsed = parse_juniper_trpz_flash(string_table)
    result = list(discover_juniper_trpz_flash(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"levels": (90.0, 95.0)},
            [["51439616", "62900224"]],
            [
                0,
                "Used: 49.1 MiB of 60.0 MiB ",
                [("used", 51439616.0, 56610201.6, 59755212.8, 0, 62900224.0)],
            ],
        ),
    ],
)
def test_check_juniper_trpz_flash(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for juniper_trpz_flash check."""
    parsed = parse_juniper_trpz_flash(string_table)
    result = list(check_juniper_trpz_flash(item, params, parsed))
    assert result == expected_results
