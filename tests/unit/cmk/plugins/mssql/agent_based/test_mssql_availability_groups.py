#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.mssql.agent_based.mssql_availability_groups import (
    AGAttributes,
    check_mssql_availability_groups,
    discover_mssql_availability_groups,
    ErrorMessage,
    parse_mssql_availability_groups,
    Section,
    SyncState,
)


@pytest.mark.parametrize(
    "string_table,parsed_section",
    [
        pytest.param(
            [
                ["Some-name", "SQL\\\\SOME-INSTANCE-001", "2", "HEALTHY", "ONLINE"],
            ],
            {
                "Some-name": AGAttributes(
                    primary_replica="SQL\\\\SOME-INSTANCE-001", sync_state=SyncState.HEALTHY
                )
            },
            id="Healthy sync state",
        ),
        pytest.param(
            [
                ["Some-name", "SQL\\\\SOME-INSTANCE-001", "0", "NOT_HEALTHY", "ONLINE_IN_PROGRESS"],
            ],
            {
                "Some-name": AGAttributes(
                    primary_replica="SQL\\\\SOME-INSTANCE-001", sync_state=SyncState.NOT_HEALTHY
                )
            },
            id="Unhealthy sync state",
        ),
        pytest.param(
            [
                ["Some-name", "SQL\\\\SOME-INSTANCE-001", "1", "PARTIALLY_HEALTHY", "ONLINE"],
            ],
            {
                "Some-name": AGAttributes(
                    primary_replica="SQL\\\\SOME-INSTANCE-001",
                    sync_state=SyncState.PARTIALLY_HEALTHY,
                )
            },
            id="Partially healthy sync state",
        ),
        pytest.param(
            [
                ["SQL\\\\SOME-INSTANCE-001 ERROR: Danger danger"],
            ],
            ErrorMessage(instance="SQL\\\\SOME-INSTANCE-001", message="Danger danger"),
            id="Error message",
        ),
    ],
)
def test_parse_mssql_availability_groups(
    string_table: StringTable, parsed_section: Section
) -> None:
    assert parse_mssql_availability_groups(string_table) == parsed_section


@pytest.mark.parametrize(
    "section,discovered_services",
    [
        pytest.param(
            {
                "Some-name": AGAttributes(
                    primary_replica="SQL\\\\SOME-INSTANCE-001", sync_state=SyncState.HEALTHY
                )
            },
            [Service(item="Some-name")],
            id="Valid service is discovered",
        ),
        pytest.param(
            ErrorMessage(instance="SQL\\\\SOME-INSTANCE-001", message="Danger danger"),
            [],
            id="No service is discovered if there's an error",
        ),
    ],
)
def test_discover_mssql_availability_groups(
    section: Section, discovered_services: Sequence[Service]
) -> None:
    assert list(discover_mssql_availability_groups(section)) == discovered_services


@pytest.mark.parametrize(
    "section,check_results",
    [
        pytest.param(
            {
                "Some-name": AGAttributes(
                    primary_replica="SQL\\\\SOME-INSTANCE-001", sync_state=SyncState.HEALTHY
                )
            },
            [
                Result(state=State.OK, summary="Primary replica: SQL\\\\SOME-INSTANCE-001"),
                Result(
                    state=State.OK,
                    summary="Synchronization state: HEALTHY",
                ),
            ],
            id="Healthy sync state is OK",
        ),
        pytest.param(
            {
                "Some-name": AGAttributes(
                    primary_replica="SQL\\\\SOME-INSTANCE-001", sync_state=SyncState.NOT_HEALTHY
                )
            },
            [
                Result(state=State.OK, summary="Primary replica: SQL\\\\SOME-INSTANCE-001"),
                Result(
                    state=State.CRIT,
                    summary="Synchronization state: NOT_HEALTHY",
                ),
            ],
            id="Unhealthy sync state is CRIT",
        ),
        pytest.param(
            {
                "Some-name": AGAttributes(
                    primary_replica="SQL\\\\SOME-INSTANCE-001",
                    sync_state=SyncState.PARTIALLY_HEALTHY,
                )
            },
            [
                Result(state=State.OK, summary="Primary replica: SQL\\\\SOME-INSTANCE-001"),
                Result(
                    state=State.WARN,
                    summary="Synchronization state: PARTIALLY_HEALTHY",
                ),
            ],
            id="Partially healthy sync state is WARN",
        ),
        pytest.param(
            ErrorMessage(instance="SQL\\\\SOME-INSTANCE-001", message="Danger danger"),
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Error message from instance SQL\\\\SOME-INSTANCE-001: Danger danger",
                )
            ],
            id="State is UNKNOWN if there's an error",
        ),
    ],
)
def test_check_mssql_availability_groups(section: Section, check_results: Sequence[Result]) -> None:
    assert list(check_mssql_availability_groups(item="Some-name", section=section)) == check_results
