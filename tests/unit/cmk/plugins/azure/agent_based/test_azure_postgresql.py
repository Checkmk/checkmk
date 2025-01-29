#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.azure.agent_based.azure_postgresql import (
    check_plugin_azure_postgresql_connections,
    check_replication,
)
from cmk.plugins.lib.azure import AzureMetric, check_connections, Resource, Section


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        pytest.param(
            {
                "checkmk-postgresql-single-server": Resource(
                    id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforPostgreSQL/servers/checkmk-postgresql-single-server",
                    name="checkmk-postgresql-single-server",
                    type="Microsoft.DBforPostgreSQL/servers",
                    group="BurningMan",
                    location="westeurope",
                    metrics={
                        "maximum_pg_replica_log_delay_in_seconds": AzureMetric(
                            name="pg_replica_log_delay_in_seconds",
                            aggregation="maximum",
                            value=2.0,
                            unit="seconds",
                        ),
                    },
                )
            },
            "checkmk-postgresql-single-server",
            {"levels": (1.0, 5.0)},
            [
                Result(
                    state=State.WARN,
                    summary="Replication lag: 2 seconds (warn/crit at 1 second/5 seconds)",
                ),
                Metric("replication_lag", 2.0, levels=(1.0, 5.0)),
            ],
            id="single server",
        ),
        pytest.param(
            {
                "checkmk-postgres-flexible-server": Resource(
                    id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforPostgreSQL/flexibleServers/checkmk-postgres-flexible-server",
                    name="checkmk-postgres-flexible-server",
                    type="Microsoft.DBforPostgreSQL/flexibleServers",
                    group="BurningMan",
                    location="westeurope",
                    metrics={
                        "maximum_physical_replication_delay_in_seconds": AzureMetric(
                            name="maximum_physical_replication_delay_in_seconds",
                            aggregation="maximum",
                            value=6.0,
                            unit="seconds",
                        ),
                    },
                )
            },
            "checkmk-postgres-flexible-server",
            {"levels": (1.0, 5.0)},
            [
                Result(
                    state=State.CRIT,
                    summary="Replication lag: 6 seconds (warn/crit at 1 second/5 seconds)",
                ),
                Metric("replication_lag", 6.0, levels=(1.0, 5.0)),
            ],
            id="flexible server",
        ),
    ],
)
def test_check_replication(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_replication()(item, params, section)) == expected_result


def test_azure_postgresql_connections_active_connections_lower() -> None:
    assert list(
        check_plugin_azure_postgresql_connections.check_function(
            "item",
            {"active_connections_lower": (11, 9)},
            {
                "item": Resource(
                    id="id",
                    name="name",
                    type="type",
                    group="group",
                    location="location",
                    metrics={
                        "average_active_connections": AzureMetric(
                            name="name",
                            aggregation="aggregation",
                            value=10,
                            unit="unit",
                        )
                    },
                )
            },
        )
    ) == [
        Result(state=State.WARN, summary="Active connections: 10 (warn/crit below 11/9)"),
        Metric("active_connections", 10.0),
    ]


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        pytest.param(
            {
                "checkmk-postgres-single-server": Resource(
                    id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforPostgreSQL/servers/checkmk-postgres-single-server",
                    name="checkmk-postgres-single-server",
                    type="Microsoft.DBforPostgreSQL/servers",
                    group="BurningMan",
                    location="westeurope",
                    metrics={
                        "average_active_connections": AzureMetric(
                            name="active_connections",
                            aggregation="average",
                            value=6.0,
                            unit="count",
                        ),
                        "total_connections_failed": AzureMetric(
                            name="connections_failed",
                            aggregation="total",
                            value=2.0,
                            unit="count",
                        ),
                    },
                )
            },
            "checkmk-postgres-single-server",
            {"active_connections": (5, 10), "failed_connections": (1, 2)},
            [
                Result(state=State.WARN, summary="Active connections: 6 (warn/crit at 5/10)"),
                Metric("active_connections", 6.0, levels=(5.0, 10.0)),
                Result(state=State.CRIT, summary="Failed connections: 2 (warn/crit at 1/2)"),
                Metric("failed_connections", 2.0, levels=(1.0, 2.0)),
            ],
            id="single server",
        ),
        pytest.param(
            {
                "checkmk-postgres-flexible-server": Resource(
                    id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforPostgreSQL/flexibleServers/checkmk-postgres-flexible-server",
                    name="checkmk-postgres-flexible-server",
                    type="Microsoft.DBforPostgreSQL/flexibleServers",
                    group="BurningMan",
                    location="westeurope",
                    metrics={
                        "average_active_connections": AzureMetric(
                            name="active_connections",
                            aggregation="average",
                            value=4.0,
                            unit="count",
                        ),
                        "total_connections_failed": AzureMetric(
                            name="connections_failed",
                            aggregation="total",
                            value=3.0,
                            unit="count",
                        ),
                    },
                )
            },
            "checkmk-postgres-flexible-server",
            {"active_connections": (5, 10), "failed_connections": (1, 2)},
            [
                Result(state=State.OK, summary="Active connections: 4"),
                Metric("active_connections", 4.0, levels=(5.0, 10.0)),
                Result(state=State.CRIT, summary="Failed connections: 3 (warn/crit at 1/2)"),
                Metric("failed_connections", 3.0, levels=(1.0, 2.0)),
            ],
            id="flexible server",
        ),
    ],
)
def test_check_connections(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_connections()(item, params, section)) == expected_result
