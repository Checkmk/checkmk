#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.mysql.agent_based.mysql_ping import (
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
            [Service(item="mysql"), Service(item="elephant"), Service(item="moth")],
        ),
    ],
)
def test_discover_mysql_ping(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_mysql_ping(string_table)
    result = list(discover_mysql_ping(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "mysql",
            [
                ["this", "line", "is", "no", "longer", "ignored"],
                ["[[elephant]]"],
                ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
                ["[[moth]]"],
                ["mysqld", "is", "alive"],
            ],
            [Result(state=State.CRIT, summary="this line is no longer ignored")],
        ),
        (
            "elephant",
            [
                ["this", "line", "is", "no", "longer", "ignored"],
                ["[[elephant]]"],
                ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
                ["[[moth]]"],
                ["mysqld", "is", "alive"],
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="mysqladmin: connect to server at 'localhost' failed",
                )
            ],
        ),
        (
            "moth",
            [
                ["this", "line", "is", "no", "longer", "ignored"],
                ["[[elephant]]"],
                ["mysqladmin:", "connect", "to", "server", "at", "'localhost'", "failed"],
                ["[[moth]]"],
                ["mysqld", "is", "alive"],
            ],
            [Result(state=State.OK, summary="MySQL Daemon is alive")],
        ),
    ],
)
def test_check_mysql_ping(
    item: str, string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    parsed = parse_mysql_ping(string_table)
    result = list(check_mysql_ping(item, parsed))
    assert result == expected_results
