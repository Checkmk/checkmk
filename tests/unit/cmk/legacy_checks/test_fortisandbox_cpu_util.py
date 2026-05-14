#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.fortisandbox_cpu_util import (
    check_fortisandbox_cpu_util,
    discover_fortisandbox_cpu_util,
    parse_fortisandbox_cpu_util,
)


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param([["10"]], id="single-value"),
        pytest.param([], id="empty"),
    ],
)
def test_parse_fortisandbox_cpu_util_keeps_stringtable(string_table: StringTable) -> None:
    assert parse_fortisandbox_cpu_util(string_table) == string_table


@pytest.mark.parametrize(
    "parsed, expected",
    [
        pytest.param([["10"]], [(None, {})], id="single-value"),
        pytest.param([], [], id="empty"),
        pytest.param([[]], [(None, {})], id="empty-row"),
    ],
)
def test_discover_fortisandbox_cpu_util(
    parsed: StringTable, expected: Sequence[tuple[None, Mapping[str, Any]]]
) -> None:
    assert list(discover_fortisandbox_cpu_util(parsed)) == expected


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"util": (80.0, 90.0)},
            [["10"]],
            [
                (
                    0,
                    "Total CPU: 10.00%",
                    [("util", 10, 80.0, 90.0, 0, 100)],
                ),
            ],
            id="ok",
        ),
        pytest.param(
            {"util": (80.0, 90.0)},
            [["95"]],
            [
                (
                    2,
                    "Total CPU: 95.00% (warn/crit at 80.00%/90.00%)",
                    [("util", 95, 80.0, 90.0, 0, 100)],
                ),
            ],
            id="crit",
        ),
    ],
)
def test_check_fortisandbox_cpu_util(
    params: Mapping[str, Any],
    section: StringTable,
    expected: Sequence[tuple[int, str, list[tuple[Any, ...]]]],
) -> None:
    assert list(check_fortisandbox_cpu_util(None, params, section)) == expected


def test_check_fortisandbox_cpu_util_empty_returns_none() -> None:
    assert check_fortisandbox_cpu_util(None, {"util": (80.0, 90.0)}, []) is None
