#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.base.legacy_checks.genua_carp import (
    check_genua_carp,
    inventory_genua_carp,
    parse_genua_carp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []],
            [("carp0", None), ("carp1", None), ("carp2", None)],
        ),
    ],
)
def test_inventory_genua_carp(
    string_table: Sequence[list[list[str]]],
    expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]],
) -> None:
    """Test discovery function for genua_carp check."""
    parsed = parse_genua_carp(string_table)
    result = list(inventory_genua_carp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "carp0",
            {},
            [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []],
            [0, "Node test: node in carp state master with IfLinkState up"],
        ),
        (
            "carp1",
            {},
            [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []],
            [0, "Node test: node in carp state master with IfLinkState up"],
        ),
        (
            "carp2",
            {},
            [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []],
            [1, "Node test: node in carp state init with IfLinkState down"],
        ),
    ],
)
def test_check_genua_carp(
    item: str,
    params: Mapping[str, Any],
    string_table: Sequence[list[list[str]]],
    expected_results: Sequence[Any],
) -> None:
    """Test check function for genua_carp check."""
    parsed = parse_genua_carp(string_table)
    result = list(check_genua_carp(item, params, parsed))
    assert result == expected_results
