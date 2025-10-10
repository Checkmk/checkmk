#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.mysql_ping import (
    check_mysql_ping,
    discover_mysql_ping,
    parse_mysql_ping,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["this", "line", "is", "no", "longer", "ignored"],
                ["[[elephant]]"],
                ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
                ["[[moth]]"],
                ["mysqld", "is", "alive"],
            ],
            [("mysql", {}), ("elephant", {}), ("moth", {})],
        ),
    ],
)
def test_discover_mysql_ping(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for mysql_ping check."""
    parsed = parse_mysql_ping(string_table)
    result = list(discover_mysql_ping(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "mysql",
            {},
            [
                ["this", "line", "is", "no", "longer", "ignored"],
                ["[[elephant]]"],
                ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
                ["[[moth]]"],
                ["mysqld", "is", "alive"],
            ],
            [(2, "this line is no longer ignored")],
        ),
        (
            "elephant",
            {},
            [
                ["this", "line", "is", "no", "longer", "ignored"],
                ["[[elephant]]"],
                ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
                ["[[moth]]"],
                ["mysqld", "is", "alive"],
            ],
            [(2, "mysqladmin: connect to server at 'localhost' failed")],
        ),
        (
            "moth",
            {},
            [
                ["this", "line", "is", "no", "longer", "ignored"],
                ["[[elephant]]"],
                ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
                ["[[moth]]"],
                ["mysqld", "is", "alive"],
            ],
            [(0, "MySQL Daemon is alive")],
        ),
    ],
)
def test_check_mysql_ping(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for mysql_ping check."""
    parsed = parse_mysql_ping(string_table)
    result = list(check_mysql_ping(item, params, parsed))
    assert result == expected_results
