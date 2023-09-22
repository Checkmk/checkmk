#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.postgres_instances import (
    check_postgres_instances,
    discover_postgres_instances,
    parse_postgres_instances,
)

STRING_TABLE_instance1 = [
    ["[[[instance1]]]"],
    [
        "30611",
        "/usr/lib/postgresql/10/bin/postgres",
        "-D",
        "/var/lib/postgresql/10/main",
        "-c",
        "config_file=/etc/postgresql/10/main/postgresql.conf",
    ],
]

STRING_TABLE_instance2 = [
    ["[[[instance2]]]"],
    [
        "psql (PostgreSQL) 10.12 (Ubuntu 10.12-0ubuntu0.18.04.1)",
    ],
]

STRING_TABLE_legacy = [
    [
        "14278",
        "/postgres/9.3.15/bin/postgres",
        "-D",
        "/postgres/JIRAAPP",
    ],
]

STRING_TABLE_VERSION = [
    ["[[[jiraapp]]]"],
    [
        "PostgreSQL",
        "9.3.15",
        "on",
        "x86_64-unknown-linux-gnu,",
        "compiled",
        "by",
        "gcc",
        "(GCC)",
        "4.1.2",
        "20080704",
        "(Red",
        "Hat",
        "4.1.2-55),",
        "64-bit",
    ],
]


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_instance1,
            [Service(item="INSTANCE1")],
        ),
        pytest.param(
            STRING_TABLE_instance2,
            [Service(item="INSTANCE2")],
        ),
        pytest.param(
            STRING_TABLE_instance1 + STRING_TABLE_instance2,
            [Service(item="INSTANCE1"), Service(item="INSTANCE2")],
        ),
        pytest.param(
            STRING_TABLE_legacy,
            [Service(item="JIRAAPP")],
        ),
    ],
)
def test_discover_postgres_instances(
    string_table: StringTable, expected_result: DiscoveryResult
) -> None:
    assert (
        list(discover_postgres_instances(parse_postgres_instances(string_table))) == expected_result
    )


@pytest.mark.parametrize(
    ["item", "string_table", "expected_result"],
    [
        pytest.param(
            "INSTANCE1",
            STRING_TABLE_instance1,
            [
                Result(
                    state=State.OK,
                    summary="Status: running with PID 30611",
                ),
            ],
        ),
        pytest.param(
            "INSTANCE2",
            STRING_TABLE_instance2,
            [
                Result(
                    state=State.CRIT,
                    summary="Instance INSTANCE2 not running or postgres DATADIR name is not identical "
                    "with instance name.",
                )
            ],
        ),
        pytest.param(
            "INSTANCE3",
            STRING_TABLE_instance1 + STRING_TABLE_instance2,
            [
                Result(
                    state=State.CRIT,
                    summary="Instance INSTANCE3 not running or postgres DATADIR name is not identical with instance name.",
                )
            ],
        ),
        pytest.param(
            "JIRAAPP",
            STRING_TABLE_legacy,
            [Result(state=State.OK, summary="Status: running with PID 14278")],
        ),
    ],
)
def test_check_postgres_instances(
    item: str,
    string_table: StringTable,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_postgres_instances(
                item=item,
                section=parse_postgres_instances(string_table),
            )
        )
        == expected_result
    )
