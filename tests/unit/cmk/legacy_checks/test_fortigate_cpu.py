#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Service, StringTable
from cmk.legacy_checks.fortigate_cpu import (
    check_fortigate_cpu,
    discover_fortigate_cpu,
    parse_fortigate_cpu,
)


def test_parse_fortigate_cpu_keeps_stringtable() -> None:
    string_table = [["25"], ["31"]]
    assert parse_fortigate_cpu(string_table) == string_table


def test_parse_fortigate_cpu_empty_returns_none() -> None:
    assert parse_fortigate_cpu([]) is None


def test_discover_fortigate_cpu() -> None:
    parsed = [["25"], ["31"]]
    assert list(discover_fortigate_cpu(parsed)) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected",
    [
        pytest.param(
            {"util": (80.0, 90.0)},
            [["25"], ["31"]],
            (
                0,
                "Total CPU: 28.00% at 2 CPUs",
                [("util", 28.0, 80.0, 90.0, 0, 100)],
            ),
            id="ok",
        ),
        pytest.param(
            {"util": (80.0, 90.0)},
            [["95"], ["99"]],
            (
                2,
                "Total CPU: 97.00% (warn/crit at 80.00%/90.00%) at 2 CPUs",
                [("util", 97.0, 80.0, 90.0, 0, 100)],
            ),
            id="crit",
        ),
    ],
)
def test_check_fortigate_cpu(
    params: Mapping[str, Any],
    section: StringTable,
    expected: tuple[int, str, list[tuple[Any, ...]]],
) -> None:
    assert check_fortigate_cpu(None, params, section) == expected


def test_check_fortigate_cpu_empty_returns_none() -> None:
    assert check_fortigate_cpu(None, {"util": (80.0, 90.0)}, []) is None
