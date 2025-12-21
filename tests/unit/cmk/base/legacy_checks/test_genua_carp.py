#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State
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
            [Service(item="carp0"), Service(item="carp1"), Service(item="carp2")],
        ),
    ],
)
def test_inventory_genua_carp(
    string_table: Sequence[list[list[str]]],
    expected_discoveries: Sequence[Service],
) -> None:
    """Test discovery function for genua_carp check."""
    parsed = parse_genua_carp(string_table)
    assert list(inventory_genua_carp(parsed)) == expected_discoveries


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "carp0",
            [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []],
            [
                Result(
                    state=State.OK,
                    summary="Node test: node in carp state master with IfLinkState up",
                )
            ],
        ),
        (
            "carp1",
            [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []],
            [
                Result(
                    state=State.OK,
                    summary="Node test: node in carp state master with IfLinkState up",
                )
            ],
        ),
        (
            "carp2",
            [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []],
            [
                Result(
                    state=State.WARN,
                    summary="Node test: node in carp state init with IfLinkState down",
                )
            ],
        ),
    ],
)
def test_check_genua_carp(
    item: str,
    string_table: Sequence[list[list[str]]],
    expected_results: Sequence[Result],
) -> None:
    """Test check function for genua_carp check."""
    parsed = parse_genua_carp(string_table)
    assert list(check_genua_carp(item, parsed)) == expected_results
