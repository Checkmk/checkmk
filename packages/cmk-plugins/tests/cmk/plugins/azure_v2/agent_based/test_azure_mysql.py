#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.azure_v2.agent_based.azure_mysql import (
    check_azure_mysql_memory,
    check_plugin_azure_mysql_connections,
    check_plugin_azure_mysql_cpu,
    check_plugin_azure_mysql_network,
    check_plugin_azure_mysql_replication,
    check_plugin_azure_mysql_storage,
    check_replication,
    inventory_plugin_azure_mysql,
)
from cmk.plugins.azure_v2.agent_based.lib import (
    AzureMetric,
    Resource,
)

from .inventory import get_inventory_value


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-single-server",
                name="checkmk-mysql-single-server",
                type="Microsoft.DBforMySQL/servers",
                group="BurningMan",
                location="westeurope",
                metrics={
                    "maximum_seconds_behind_master": AzureMetric(
                        name="seconds_behind_master",
                        aggregation="maximum",
                        value=2.0,
                        unit="seconds",
                    ),
                },
            ),
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
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/flexibleServers/checkmk-mysql-flexible-server",
                name="checkmk-mysql-flexible-server",
                type="Microsoft.DBforMySQL/flexibleServers",
                group="BurningMan",
                location="westeurope",
                metrics={
                    "maximum_replication_lag": AzureMetric(
                        name="replication_lag",
                        aggregation="maximum",
                        value=6.0,
                        unit="seconds",
                    ),
                },
            ),
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
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/flexibleServers/checkmk-mysql-flexible-server",
                name="checkmk-mysql-flexible-server",
                type="Microsoft.DBforMySQL/flexibleServers",
                group="BurningMan",
                location="westeurope",
                metrics={
                    "maximum_replication_lag": AzureMetric(
                        name="replication_lag",
                        aggregation="maximum",
                        value=65.0,
                        unit="seconds",
                    ),
                },
            ),
            check_plugin_azure_mysql_replication.check_default_parameters,
            [
                Result(
                    state=State.WARN,
                    summary="Replication lag: 1 minute 5 seconds (warn/crit at 1 minute 0 seconds/10 minutes 0 seconds)",
                ),
                Metric("replication_lag", 65.0, levels=(60, 600)),
            ],
            id="default params",
        ),
    ],
)
def test_check_replication(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    assert (
        list(check_replication()("Replication", params, {"Replication": section}))
        == expected_result
    )


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-single-server",
                name="checkmk-mysql-single-server",
                type="Microsoft.DBforMySQL/servers",
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
            ),
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
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/flexibleServers/checkmk-mysql-flexible-server",
                name="checkmk-mysql-flexible-server",
                type="Microsoft.DBforMySQL/flexibleServers",
                group="BurningMan",
                location="westeurope",
                metrics={
                    "average_active_connections": AzureMetric(
                        name="active_connections",
                        aggregation="average",
                        value=4.0,
                        unit="count",
                    ),
                    "total_aborted_connections": AzureMetric(
                        name="aborted_connections",
                        aggregation="total",
                        value=3.0,
                        unit="count",
                    ),
                },
            ),
            check_plugin_azure_mysql_connections.check_default_parameters,
            [
                Result(state=State.OK, summary="Active connections: 4"),
                Metric("active_connections", 4.0),
                Result(state=State.CRIT, summary="Failed connections: 3 (warn/crit at 1/1)"),
                Metric("failed_connections", 3.0, levels=(1.0, 1.0)),
            ],
            id="flexible server",
        ),
    ],
)
def test_check_connections(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    assert (
        list(check_plugin_azure_mysql_connections.check_function(params, section))
        == expected_result
    )


def test_azure_mysql_connections_active_connections_lower() -> None:
    assert list(
        check_plugin_azure_mysql_connections.check_function(
            {"active_connections_lower": (11, 9)},
            Resource(
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
            ),
        )
    ) == [
        Result(state=State.WARN, summary="Active connections: 10 (warn/crit below 11/9)"),
        Metric("active_connections", 10.0),
    ]


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="test-id",
                name="test-name",
                type="Microsoft.DBforMySQL/servers",
                group="test-group",
                location="westeurope",
                metrics={
                    "average_memory_percent": AzureMetric(
                        name="memory_percent",
                        aggregation="average",
                        value=50.0,
                        unit="percent",
                    ),
                },
            ),
            {"levels": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Memory utilization: 50.00%"),
                Metric("mem_used_percent", 50.0, levels=(80.0, 90.0)),
            ],
            id="memory ok",
        ),
        pytest.param(
            Resource(
                id="test-id",
                name="test-name",
                type="Microsoft.DBforMySQL/servers",
                group="test-group",
                location="westeurope",
                metrics={
                    "average_memory_percent": AzureMetric(
                        name="memory_percent",
                        aggregation="average",
                        value=96.03,
                        unit="percent",
                    ),
                },
            ),
            {"levels": (80.0, 90.0)},
            [
                Result(
                    state=State.CRIT,
                    summary="Memory utilization: 96.03% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("mem_used_percent", 96.03, levels=(80.0, 90.0)),
            ],
            id="memory crit",
        ),
    ],
)
def test_check_memory(
    section: Resource, params: Mapping[str, Any], expected_result: CheckResult
) -> None:
    assert list(check_azure_mysql_memory("Memory", params, section)) == expected_result


def test_azure_mysql_inventory() -> None:
    section = Resource(
        id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-single-server",
        name="checkmk-mysql-single-server",
        type="Microsoft.DBforMySQL/servers",
        group="BurningMan",
        location="westeurope",
        metrics={
            "maximum_seconds_behind_master": AzureMetric(
                name="seconds_behind_master",
                aggregation="maximum",
                value=2.0,
                unit="seconds",
            ),
        },
    )
    inventory = inventory_plugin_azure_mysql.inventory_function(section)
    assert get_inventory_value(inventory, "region") == "westeurope"


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="test-id",
                name="test-name",
                type="Microsoft.DBforMySQL/servers",
                group="test-group",
                location="westeurope",
                metrics={
                    "average_io_consumption_percent": AzureMetric(
                        name="io_consumption_percent",
                        aggregation="average",
                        value=50.0,
                        unit="percent",
                    ),
                    "average_storage_percent": AzureMetric(
                        name="storage_percent",
                        aggregation="average",
                        value=60.0,
                        unit="percent",
                    ),
                    "average_serverlog_storage_percent": AzureMetric(
                        name="serverlog_storage_percent",
                        aggregation="average",
                        value=70.0,
                        unit="percent",
                    ),
                },
            ),
            {
                "io_consumption": ("fixed", (80.0, 90.0)),
                "storage": ("fixed", (80.0, 90.0)),
                "serverlog_storage": ("fixed", (80.0, 90.0)),
            },
            [
                Result(state=State.OK, summary="IO: 50.00%"),
                Metric("io_consumption_percent", 50.0, levels=(80.0, 90.0)),
                Result(state=State.OK, summary="Storage: 60.00%"),
                Metric("storage_percent", 60.0, levels=(80.0, 90.0)),
                Result(state=State.OK, summary="Server log storage: 70.00%"),
                Metric("serverlog_storage_percent", 70.0, levels=(80.0, 90.0)),
            ],
            id="all ok",
        ),
        pytest.param(
            Resource(
                id="test-id",
                name="test-name",
                type="Microsoft.DBforMySQL/servers",
                group="test-group",
                location="westeurope",
                metrics={
                    "average_storage_percent": AzureMetric(
                        name="storage_percent",
                        aggregation="average",
                        value=85.0,
                        unit="percent",
                    ),
                },
            ),
            {
                "storage": ("fixed", (80.0, 90.0)),
            },
            [
                Result(state=State.WARN, summary="Storage: 85.00% (warn/crit at 80.00%/90.00%)"),
                Metric("storage_percent", 85.0, levels=(80.0, 90.0)),
            ],
            id="storage warn",
        ),
    ],
)
def test_check_storage(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    assert list(check_plugin_azure_mysql_storage.check_function(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="test-id",
                name="test-name",
                type="Microsoft.DBforMySQL/servers",
                group="test-group",
                location="westeurope",
                metrics={
                    "total_network_bytes_ingress": AzureMetric(
                        name="ingress",
                        aggregation="total",
                        value=1000.0,
                        unit="bytes",
                    ),
                    "total_network_bytes_egress": AzureMetric(
                        name="egress",
                        aggregation="total",
                        value=1500.0,
                        unit="bytes",
                    ),
                },
            ),
            {
                "ingress_levels": ("fixed", (5000, 10000)),
                "egress_levels": ("fixed", (1000, 2000)),
            },
            [
                Result(state=State.OK, summary="Network in: 1000 B"),
                Metric("ingress", 1000.0, levels=(5000.0, 10000.0)),
                Result(
                    state=State.WARN, summary="Network out: 1.46 KiB (warn/crit at 1000 B/1.95 KiB)"
                ),
                Metric("egress", 1500.0, levels=(1000.0, 2000.0)),
            ],
            id="network warn",
        ),
    ],
)
def test_check_network(
    section: Resource, params: Mapping[str, Any], expected_result: CheckResult
) -> None:
    assert list(check_plugin_azure_mysql_network.check_function(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="test-id",
                name="test-name",
                type="Microsoft.DBforMySQL/servers",
                group="test-group",
                location="westeurope",
                metrics={
                    "average_cpu_percent": AzureMetric(
                        name="cpu_percent",
                        aggregation="average",
                        value=50.0,
                        unit="percent",
                    ),
                },
            ),
            {"levels": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="CPU utilization: 50.00%"),
                Metric("util", 50.0, levels=(80.0, 90.0)),
            ],
            id="cpu ok",
        ),
        pytest.param(
            Resource(
                id="test-id",
                name="test-name",
                type="Microsoft.DBforMySQL/servers",
                group="test-group",
                location="westeurope",
                metrics={
                    "average_cpu_percent": AzureMetric(
                        name="cpu_percent",
                        aggregation="average",
                        value=95.0,
                        unit="percent",
                    ),
                },
            ),
            {"levels": (80.0, 90.0)},
            [
                Result(
                    state=State.CRIT,
                    summary="CPU utilization: 95.00% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("util", 95.0, levels=(80.0, 90.0)),
            ],
            id="cpu crit",
        ),
    ],
)
def test_check_cpu(
    section: Resource, params: Mapping[str, Any], expected_result: CheckResult
) -> None:
    assert list(check_plugin_azure_mysql_cpu.check_function(params, section)) == expected_result
