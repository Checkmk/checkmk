#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.postgres_instances import parse_postgres_instances


@pytest.mark.parametrize(
    ["string_table", "expected_result"],
    [
        pytest.param(
            [
                ["[[[instance1]]]"],
                [
                    "30611",
                    "/usr/lib/postgresql/10/bin/postgres",
                    "-D",
                    "/var/lib/postgresql/10/main",
                    "-c",
                    "config_file=/etc/postgresql/10/main/postgresql.conf",
                ],
            ],
            [Service(item="INSTANCE1")],
        ),
        pytest.param(
            [
                ["[[[instance2]]]"],
                [
                    "psql (PostgreSQL) 10.12 (Ubuntu 10.12-0ubuntu0.18.04.1)",
                ],
            ],
            [Service(item="INSTANCE2")],
        ),
        pytest.param(
            [
                ["[[[instance1]]]"],
                [
                    "30611",
                    "/usr/lib/postgresql/10/bin/postgres",
                    "-D",
                    "/var/lib/postgresql/10/main",
                    "-c",
                    "config_file=/etc/postgresql/10/main/postgresql.conf",
                ],
                ["[[[instance2]]]"],
                [
                    "psql (PostgreSQL) 10.12 (Ubuntu 10.12-0ubuntu0.18.04.1)",
                ],
            ],
            [Service(item="INSTANCE1"), Service(item="INSTANCE2")],
        ),
        pytest.param(
            [
                [
                    "14278",
                    "/postgres/9.3.15/bin/postgres",
                    "-D",
                    "/postgres/JIRAAPP",
                ],
            ],
            [Service(item="JIRAAPP")],
        ),
    ],
)
def test_discover_postgres_instances(
    fix_register: FixRegister, string_table: StringTable, expected_result: DiscoveryResult
) -> None:
    assert (
        list(
            fix_register.check_plugins[CheckPluginName("postgres_instances")].discovery_function(
                parse_postgres_instances(string_table)
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ["item", "string_table", "expected_result"],
    [
        pytest.param(
            "INSTANCE1",
            [
                ["[[[instance1]]]"],
                [
                    "30611",
                    "/usr/lib/postgresql/10/bin/postgres",
                    "-D",
                    "/var/lib/postgresql/10/main",
                    "-c",
                    "config_file=/etc/postgresql/10/main/postgresql.conf",
                ],
            ],
            [Result(state=State.OK, summary="Status: running with PID 30611")],
        ),
        pytest.param(
            "INSTANCE2",
            [
                ["[[[instance2]]]"],
                [
                    "psql (PostgreSQL) 10.12 (Ubuntu 10.12-0ubuntu0.18.04.1)",
                ],
            ],
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
            [
                ["[[[instance1]]]"],
                [
                    "30611",
                    "/usr/lib/postgresql/10/bin/postgres",
                    "-D",
                    "/var/lib/postgresql/10/main",
                    "-c",
                    "config_file=/etc/postgresql/10/main/postgresql.conf",
                ],
                ["[[[instance2]]]"],
                [
                    "psql (PostgreSQL) 10.12 (Ubuntu 10.12-0ubuntu0.18.04.1)",
                ],
            ],
            [
                Result(
                    state=State.CRIT,
                    summary="Instance INSTANCE3 not running or postgres DATADIR name is not identical with instance name.",
                )
            ],
        ),
        pytest.param(
            "JIRAAPP",
            [
                [
                    "14278",
                    "/postgres/9.3.15/bin/postgres",
                    "-D",
                    "/postgres/JIRAAPP",
                ],
            ],
            [Result(state=State.OK, summary="Status: running with PID 14278")],
        ),
    ],
)
def test_check_postgres_instances(
    fix_register: FixRegister,
    item: str,
    string_table: StringTable,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            fix_register.check_plugins[CheckPluginName("postgres_instances")].check_function(
                item=item,
                params={},
                section=parse_postgres_instances(string_table),
            )
        )
        == expected_result
    )
