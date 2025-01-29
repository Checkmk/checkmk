#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.postgres_instances import (
    check_postgres_instances,
    check_postgres_processes,
    discover_postgres_instances,
    parse_postgres_instances,
    parse_postgres_version,
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
    ["instances_string_table", "version_string_table", "expected_result"],
    [
        pytest.param(
            STRING_TABLE_instance1,
            [],
            [Service(item="INSTANCE1")],
        ),
        pytest.param(
            STRING_TABLE_instance2,
            [],
            [Service(item="INSTANCE2")],
        ),
        pytest.param(
            STRING_TABLE_instance1 + STRING_TABLE_instance2,
            [],
            [Service(item="INSTANCE1"), Service(item="INSTANCE2")],
        ),
        pytest.param(
            STRING_TABLE_legacy,
            STRING_TABLE_VERSION,
            [Service(item="JIRAAPP")],
        ),
    ],
)
def test_discover_postgres_instances(
    instances_string_table: StringTable,
    version_string_table: StringTable,
    expected_result: DiscoveryResult,
) -> None:
    assert (
        list(
            discover_postgres_instances(
                parse_postgres_instances(instances_string_table),
                parse_postgres_version(version_string_table),
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ["item", "instances_string_table", "version_string_table", "expected_result"],
    [
        pytest.param(
            "INSTANCE1",
            STRING_TABLE_instance1,
            [],
            [
                Result(
                    state=State.OK,
                    summary="Status: running with PID 30611",
                ),
                Result(state=State.OK, summary="Version: not found"),
            ],
        ),
        pytest.param(
            "INSTANCE2",
            STRING_TABLE_instance2,
            [],
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "Status: instance INSTANCE2 is not running or postgres DATADIR name is not "
                        "identical with instance name"
                    ),
                ),
                Result(state=State.OK, summary="Version: not found"),
            ],
        ),
        pytest.param(
            "INSTANCE3",
            STRING_TABLE_instance1 + STRING_TABLE_instance2,
            [],
            [
                Result(
                    state=State.CRIT,
                    summary=(
                        "Status: instance INSTANCE3 is not running or postgres DATADIR name is not "
                        "identical with instance name"
                    ),
                ),
                Result(state=State.OK, summary="Version: not found"),
            ],
        ),
        pytest.param(
            "JIRAAPP",
            STRING_TABLE_legacy,
            STRING_TABLE_VERSION,
            [
                Result(state=State.OK, summary="Status: running with PID 14278"),
                Result(
                    state=State.OK,
                    summary=(
                        "Version: PostgreSQL 9.3.15 on x86_64-unknown-linux-gnu, compiled by gcc "
                        "(GCC) 4.1.2 20080704 (Red Hat 4.1.2-55), 64-bit"
                    ),
                ),
            ],
        ),
    ],
)
def test_check_postgres_instances(
    item: str,
    instances_string_table: StringTable,
    version_string_table: StringTable,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_postgres_instances(
                item=item,
                section_postgres_instances=parse_postgres_instances(instances_string_table),
                section_postgres_version=parse_postgres_version(version_string_table),
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ["instances_string_table", "expected_results"],
    [
        pytest.param(
            STRING_TABLE_instance2,
            [
                Result(state=State.CRIT, summary="0", details="No process matched"),
            ],
        ),
        pytest.param(
            STRING_TABLE_instance1 + STRING_TABLE_instance2,
            [
                Result(state=State.OK, summary="1", details="PIDs"),
                Result(state=State.OK, notice="30611"),
            ],
        ),
        pytest.param(
            STRING_TABLE_legacy,
            [
                Result(state=State.OK, summary="1", details="PIDs"),
                Result(state=State.OK, notice="14278"),
            ],
        ),
    ],
)
def test_check_postgres_processes(
    instances_string_table: StringTable, expected_results: CheckResult
) -> None:
    section = parse_postgres_instances(instances_string_table)
    results = list(check_postgres_processes(section))
    assert results == expected_results
